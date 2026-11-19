"""Load test / demo-data generator for Faultkeeper's ingest pipeline.

Sends N Sentry-format envelopes spread across M distinct "bugs" from C concurrent
workers, then reports ingest throughput and latency. With --verify it waits until
the pipeline has processed everything and checks that grouping produced M issues.

Standard library only; runs anywhere Python 3.10+ runs:

    python loadtest/send_events.py --events 5000 --bugs 25 --concurrency 16 --verify
    python loadtest/send_events.py --events 600 --backdate-hours 72   # demo history
"""

from __future__ import annotations

import argparse
import http.client
import http.cookiejar
import json
import random
import statistics
import threading
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

DEFAULT_DSN = "http://79a635b512d79894d720b95fbdad5008@localhost:8000/3"  # seed_demo "load-test"

EXCEPTION_TYPES = ["TypeError", "ValueError", "KeyError", "RuntimeError", "ZeroDivisionError"]
MODULES = ["shop.cart", "shop.checkout", "shop.pricing", "shop.inventory", "shop.users"]
RELEASES = ["shop@1.4.0", "shop@1.5.0", "shop@1.5.1"]
ENVIRONMENTS = ["production", "production", "production", "staging"]
BROWSERS = ["Chrome 130", "Firefox 132", "Safari 18", "Edge 130"]


def make_bug(index: int, run_id: str) -> dict:
    module = MODULES[index % len(MODULES)]
    return {
        "type": EXCEPTION_TYPES[index % len(EXCEPTION_TYPES)],
        "module": module,
        "function": f"handler_{index}_{run_id}",
        "value": f"failure #{index} [{run_id}] for order {{order}}",
    }


def make_event(bug: dict, timestamp: float) -> dict:
    order = random.randint(1000, 99999)
    return {
        "event_id": uuid.uuid4().hex,
        "timestamp": timestamp,
        "platform": "python",
        "level": "error",
        "release": random.choice(RELEASES),
        "environment": random.choice(ENVIRONMENTS),
        "tags": {"browser": random.choice(BROWSERS), "loadtest": "true"},
        "exception": {
            "values": [
                {
                    "type": bug["type"],
                    "value": bug["value"].format(order=order),
                    "stacktrace": {
                        "frames": [
                            {"module": "shop.views", "function": "dispatch", "lineno": 40, "in_app": True},
                            {
                                "module": bug["module"],
                                "function": bug["function"],
                                "lineno": random.randint(10, 300),  # line numbers must not split issues
                                "in_app": True,
                            },
                        ]
                    },
                }
            ]
        },
    }


def envelope(event: dict) -> bytes:
    payload = json.dumps(event).encode()
    header = json.dumps({"event_id": event["event_id"]}).encode()
    item = json.dumps({"type": "event", "length": len(payload)}).encode()
    return header + b"\n" + item + b"\n" + payload + b"\n"


class Sender:
    """One keep-alive HTTP connection per worker thread."""

    def __init__(self, dsn: str) -> None:
        parts = urlsplit(dsn)
        self.public_key = parts.username or ""
        self.host = parts.hostname or "localhost"
        self.port = parts.port or (443 if parts.scheme == "https" else 80)
        self.https = parts.scheme == "https"
        self.path = f"/api/{parts.path.strip('/')}/envelope/"
        self.local = threading.local()

    def _conn(self) -> http.client.HTTPConnection:
        if not hasattr(self.local, "conn"):
            cls = http.client.HTTPSConnection if self.https else http.client.HTTPConnection
            self.local.conn = cls(self.host, self.port, timeout=30)
        return self.local.conn

    def send(self, body: bytes) -> tuple[int, float]:
        headers = {
            "Content-Type": "application/x-sentry-envelope",
            "X-Sentry-Auth": f"Sentry sentry_version=7, sentry_key={self.public_key}, sentry_client=faultkeeper-loadtest/1.0",
        }
        start = time.perf_counter()
        for attempt in range(2):
            try:
                conn = self._conn()
                conn.request("POST", self.path, body=body, headers=headers)
                response = conn.getresponse()
                response.read()
                return response.status, time.perf_counter() - start
            except (http.client.HTTPException, OSError):
                del self.local.conn  # reconnect once
                if attempt:
                    raise
        raise RuntimeError("unreachable")


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))]


def api_session(base: str, email: str, password: str) -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.open(f"{base}/api/0/auth/csrf/")
    token = next(c.value for c in jar if c.name == "csrftoken") or ""
    login = urllib.request.Request(
        f"{base}/api/0/auth/login/",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json", "X-CSRFToken": token, "Referer": base + "/"},
    )
    opener.open(login)
    return opener


def processed_totals(
    opener: urllib.request.OpenerDirector, base: str, project: str, run_id: str
) -> tuple[int, int]:
    """Issues and events created by this run (bugs carry the run id in their title)."""
    url = f"{base}/api/0/projects/{project}/issues/?status=all&limit=100&q={run_id}"
    issues = json.loads(opener.open(url).read())["results"]
    return len(issues), sum(i["times_seen"] for i in issues)


def wait_for_processing(opener, base: str, project: str, run_id: str, accepted: int, timeout: float) -> dict:
    deadline = time.time() + timeout
    while True:
        issues, seen = processed_totals(opener, base, project, run_id)
        if seen >= accepted or time.time() > deadline:
            return {"issues_created": issues, "events_processed": seen}
        time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--events", type=int, default=2000)
    parser.add_argument("--bugs", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--backdate-hours", type=float, default=0, help="spread timestamps over the past N hours")
    parser.add_argument("--verify", action="store_true", help="wait for processing and check issue count")
    parser.add_argument("--project", default="demo/load-test", help="org/project slug for --verify")
    parser.add_argument("--email", default="admin@faultkeeper.local")
    parser.add_argument("--password", default="faultkeeper")
    parser.add_argument("--json", dest="json_out", help="write results to this file")
    parser.add_argument(
        "--expect-exact",
        action="store_true",
        help="with --verify: exit 1 unless every event was accepted and grouped into exactly --bugs issues",
    )
    args = parser.parse_args()

    run_id = uuid.uuid4().hex[:8]
    bugs = [make_bug(i, run_id) for i in range(args.bugs)]
    now = time.time()
    bodies = [
        envelope(make_event(random.choice(bugs), now - random.random() * args.backdate_hours * 3600))
        for _ in range(args.events)
    ]
    sender = Sender(args.dsn)
    parts = urlsplit(args.dsn)
    base = f"{parts.scheme}://{parts.hostname}:{parts.port or 80}"
    opener = api_session(base, args.email, args.password) if args.verify else None
    statuses: dict[int, int] = {}
    latencies: list[float] = []
    lock = threading.Lock()

    def work(body: bytes) -> None:
        status, seconds = sender.send(body)
        with lock:
            statuses[status] = statuses.get(status, 0) + 1
            latencies.append(seconds * 1000)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(work, bodies))
    elapsed = time.perf_counter() - started

    results: dict = {
        "events": args.events,
        "bugs": args.bugs,
        "concurrency": args.concurrency,
        "seconds": round(elapsed, 2),
        "events_per_second": round(args.events / elapsed, 1),
        "latency_ms": {
            "p50": round(statistics.median(latencies), 1),
            "p95": round(percentile(latencies, 95), 1),
            "p99": round(percentile(latencies, 99), 1),
            "max": round(max(latencies), 1),
        },
        "status_codes": statuses,
    }
    if opener:
        results["run_id"] = run_id
        results["processing"] = wait_for_processing(
            opener, base, args.project, run_id, statuses.get(200, 0), timeout=600
        )
        # Ingest and processing run concurrently; this is when the last event was grouped.
        total = time.perf_counter() - started
        results["processing"]["seconds_until_all_processed"] = round(total, 1)
        results["processing"]["processed_per_second"] = round(
            results["processing"]["events_processed"] / total, 1
        )

    print(json.dumps(results, indent=2))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)

    if args.expect_exact:
        processing = results.get("processing", {})
        ok = (
            statuses == {200: args.events}
            and processing.get("events_processed") == args.events
            and processing.get("issues_created") == args.bugs
        )
        print("E2E CHECK:", "PASS" if ok else "FAIL")
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
