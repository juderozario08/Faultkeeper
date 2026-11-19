"""SDK-facing ingest endpoints (docs/PROTOCOL.md).

Ingest only authenticates, rate-limits, parses, and enqueues. It never processes inline.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .auth import IngestError, authenticate, check_rate_limit
from .compression import decompress
from .envelope import EnvelopeError, parse_envelope
from .queue import enqueue_event

logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": (
        "Content-Type, Content-Encoding, X-Sentry-Auth, sentry-trace, baggage"
    ),
    "Access-Control-Expose-Headers": "X-Sentry-Rate-Limits, Retry-After",
    "Access-Control-Max-Age": "3600",
}


def _with_cors(response: HttpResponse) -> HttpResponse:
    for name, value in CORS_HEADERS.items():
        response[name] = value
    return response


def _error(exc: IngestError) -> HttpResponse:
    response = JsonResponse({"detail": exc.detail}, status=exc.status)
    for name, value in exc.headers.items():
        response[name] = value
    return _with_cors(response)


def _read_body(request: HttpRequest) -> bytes:
    max_bytes: int = settings.INGEST_MAX_BYTES
    declared = request.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise IngestError(413, "payload too large")
    try:
        raw = request.body
    except RequestDataTooBig as exc:
        raise IngestError(413, "payload too large") from exc
    return decompress(raw, request.headers.get("Content-Encoding"), max_bytes)


def _capture(project_id: int, request: HttpRequest, body: bytes) -> None:
    """Dev aid: save raw bodies to build SDK compatibility fixtures."""
    directory = settings.INGEST_CAPTURE_DIR
    if not directory:
        return
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now(UTC):%Y%m%dT%H%M%S%f}-p{project_id}"
    (path / f"{stem}.envelope").write_bytes(body)
    meta = {k: v for k, v in request.headers.items() if k.lower() != "cookie"}
    (path / f"{stem}.headers.json").write_text(json.dumps(meta, indent=2))


def _normalize_event_id(value: Any) -> str:
    try:
        return uuid.UUID(str(value)).hex
    except (ValueError, TypeError):
        return uuid.uuid4().hex


async def _enqueue(project_id: int, event: dict[str, Any], received_at: str) -> None:
    """Enqueueing does blocking network I/O (Celery -> Redis), so run it off the event
    loop without pinning it to Django's single thread-sensitive executor. Eager Celery
    (tests) processes inline and touches the DB, so it must stay thread-sensitive."""
    thread_sensitive = bool(settings.CELERY_TASK_ALWAYS_EAGER)
    await sync_to_async(enqueue_event, thread_sensitive=thread_sensitive)(
        project_id, event, received_at
    )


async def _accept_event(project_id: int, event: Any, fallback_id: Any = None) -> str:
    if not isinstance(event, dict):
        raise IngestError(400, "event must be a JSON object")
    event_id = _normalize_event_id(event.get("event_id") or fallback_id)
    event["event_id"] = event_id
    await _enqueue(project_id, event, datetime.now(UTC).isoformat())
    return event_id


async def _ingest(request: HttpRequest, project_id: int, kind: str) -> HttpResponse:
    if request.method == "OPTIONS":
        return _with_cors(HttpResponse(status=200))
    if request.method != "POST":
        return _with_cors(JsonResponse({"detail": "method not allowed"}, status=405))
    try:
        key = await authenticate(request, project_id)
        await check_rate_limit(key)
        body = _read_body(request)
        _capture(project_id, request, body)

        if kind == "store":
            try:
                event = json.loads(body)
            except (ValueError, UnicodeDecodeError) as exc:
                raise IngestError(400, "body is not valid JSON") from exc
            return _with_cors(JsonResponse({"id": await _accept_event(project_id, event)}))

        envelope = parse_envelope(body)
        event_id: str | None = None
        for item in envelope.items:
            if item.type == "event":
                event_id = await _accept_event(
                    project_id, item.json(), envelope.headers.get("event_id")
                )
            # Other item types are acknowledged and dropped (PROTOCOL.md §4).
        if event_id is None and envelope.headers.get("event_id"):
            event_id = _normalize_event_id(envelope.headers["event_id"])
        return _with_cors(JsonResponse({"id": event_id} if event_id else {}))
    except IngestError as exc:
        return _error(exc)
    except EnvelopeError as exc:
        return _error(IngestError(400, str(exc)))


@csrf_exempt
async def envelope_endpoint(request: HttpRequest, project_id: int) -> HttpResponse:
    return await _ingest(request, project_id, "envelope")


@csrf_exempt
async def store_endpoint(request: HttpRequest, project_id: int) -> HttpResponse:
    return await _ingest(request, project_id, "store")
