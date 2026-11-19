# Load testing

`send_events.py` sends Sentry-format envelopes concurrently to the ingest endpoint, then (with `--verify`) waits until the pipeline has processed them and checks the grouping. It uses only the standard library.

```bash
# from the host
python loadtest/send_events.py --events 5000 --bugs 25 --concurrency 16 --verify

# from inside the compose network (avoids Docker Desktop port-forwarding overhead)
docker compose run --rm --no-deps -v "$PWD/loadtest:/lt" web \
  python /lt/send_events.py --dsn http://79a635b512d79894d720b95fbdad5008@web:8000/3 \
  --events 5000 --bugs 25 --concurrency 16 --verify

# fill the dashboard with 3 days of history for a demo
python loadtest/send_events.py --events 800 --bugs 12 --backdate-hours 72
```

The default DSN is the `load-test` project from `seed_demo`, which has a high rate limit. Each event has a random line number and order ID, so `--verify` also checks that grouping ignores dynamic values: N events across M bugs must produce exactly M issues.

## Results

Environment: development stack (`docker compose up`; uvicorn with `--reload`, `DEBUG=true`, one web process) on Windows 11 with Docker Desktop, Ryzen 9 9900X. 5,000 events, 25 distinct bugs, 16 concurrent clients.

| Change | Ingest throughput | Ingest p50 / p99 | Processing throughput | Issues created |
|---|---|---|---|---|
| Baseline: sync ingest view, 2 workers (from host) | 88 ev/s | 172 / 368 ms | n/a | 25 ✓ |
| Async ingest + native asyncio Redis (from host) | 172 ev/s | 79 / 236 ms | n/a | 25 ✓ |
| Async ingest, measured inside the compose network | 205 ev/s | 77 / 120 ms | 81 ev/s (2 workers) | 25 ✓ |
| + 4 Celery worker processes | 191 ev/s | 82 / 134 ms | **150 ev/s** | 25 ✓ |

**What made the difference**
- **Async ingest (2×).** Under ASGI, Django runs synchronous views on a single shared thread, so every ingest request was serialised. The ingest path is now an `async` view. It uses a native `redis.asyncio` client for key lookups and rate limiting, and Celery publishing runs in a non-thread-sensitive executor.
- **Worker processes (1.9× processing).** Processing is CPU- and DB-bound per event, so it scales with Celery worker processes.

**Next steps** (phase 2/3): batch the `times_seen` counter updates through a Redis buffer, run multiple uvicorn workers in production mode, move ingest to Kafka, and put the Rust edge in front.

Raw JSON results are in `results/`.
