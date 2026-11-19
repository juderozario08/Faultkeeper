"""Turn an SDK event into a consistent, size-bounded, lightly scrubbed shape."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

LEVELS = {"fatal", "error", "warning", "info", "debug"}
MAX_STRING = 8192
MAX_BREADCRUMBS = 100
MAX_FRAMES = 250
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"}
LIBRARY_MARKERS = ("node_modules", "site-packages", "dist-packages", "/usr/lib/python")
# Engine-internal JS frames (e.g. `Array.reduce`), which SDKs sometimes mark in-app.
NATIVE_FILENAMES = {"<anonymous>", "native", "[native code]", "<native>"}


def _trim(value: Any, limit: int = MAX_STRING) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[: limit - 1] + "…"
    return value


def parse_timestamp(value: Any, fallback: datetime) -> datetime:
    parsed: datetime | None = None
    if isinstance(value, int | float):
        try:
            parsed = datetime.fromtimestamp(float(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            parsed = None
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.fromtimestamp(float(value), tz=UTC)
            except ValueError:
                parsed = None
    if parsed is None:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    # Clock skew guard: never accept events from the future.
    if parsed > fallback + timedelta(minutes=1):
        return fallback
    return parsed


def _values(container: Any) -> list[Any]:
    """Sentry interfaces may be `{"values": [...]}` or a bare list."""
    if isinstance(container, dict):
        container = container.get("values")
    return [v for v in container if isinstance(v, dict)] if isinstance(container, list) else []


def _default_in_app(frame: dict[str, Any]) -> bool:
    location = str(frame.get("abs_path") or frame.get("filename") or frame.get("module") or "")
    return not any(marker in location for marker in LIBRARY_MARKERS)


def _normalize_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for frame in frames[-MAX_FRAMES:]:
        frame = {k: _trim(v) for k, v in frame.items()}
        if str(frame.get("filename") or frame.get("abs_path") or "") in NATIVE_FILENAMES:
            frame["in_app"] = False
        elif not isinstance(frame.get("in_app"), bool):
            frame["in_app"] = _default_in_app(frame)
        out.append(frame)
    return out


def _normalize_exception(exc: dict[str, Any]) -> dict[str, Any]:
    exc = dict(exc)
    exc["type"] = _trim(str(exc.get("type") or "Error"), 256)
    exc["value"] = _trim(str(exc.get("value") or ""))
    stacktrace = exc.get("stacktrace")
    if isinstance(stacktrace, dict):
        frames = [f for f in stacktrace.get("frames") or [] if isinstance(f, dict)]
        exc["stacktrace"] = {**stacktrace, "frames": _normalize_frames(frames)}
    return exc


def _normalize_tags(tags: Any) -> list[list[str]]:
    pairs: list[tuple[Any, Any]] = []
    if isinstance(tags, dict):
        pairs = list(tags.items())
    elif isinstance(tags, list):
        pairs = [tuple(t) for t in tags if isinstance(t, list | tuple) and len(t) == 2]
    return [[_trim(str(k), 200), _trim(str(v), 200)] for k, v in pairs]


def _scrub_request(request: Any) -> Any:
    if not isinstance(request, dict):
        return request
    request = dict(request)
    headers = request.get("headers")
    if isinstance(headers, dict):
        request["headers"] = {
            k: ("[Filtered]" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()
        }
    elif isinstance(headers, list):
        request["headers"] = [
            [k, "[Filtered]" if str(k).lower() in SENSITIVE_HEADERS else v]
            for k, v in (h for h in headers if isinstance(h, list | tuple) and len(h) == 2)
        ]
    request.pop("cookies", None)
    return request


def message_of(event: dict[str, Any]) -> str:
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        return str(logentry.get("formatted") or logentry.get("message") or "")
    message = event.get("message")
    if isinstance(message, dict):
        return str(message.get("formatted") or message.get("message") or "")
    return str(message or "")


def normalize(payload: dict[str, Any], received_at: datetime) -> dict[str, Any]:
    event = dict(payload)
    try:
        event["event_id"] = uuid.UUID(str(event.get("event_id"))).hex
    except ValueError:
        event["event_id"] = uuid.uuid4().hex

    event["timestamp"] = parse_timestamp(event.get("timestamp"), received_at).isoformat()
    event["received"] = received_at.isoformat()

    level = str(event.get("level") or "error").lower()
    event["level"] = level if level in LEVELS else "error"
    event["platform"] = _trim(str(event.get("platform") or "other"), 64)

    for key in ("release", "environment", "dist", "logger", "transaction", "server_name"):
        if event.get(key) is not None:
            event[key] = _trim(str(event[key]), 250)

    exceptions = [_normalize_exception(e) for e in _values(event.get("exception"))]
    if exceptions:
        event["exception"] = {"values": exceptions}
    else:
        event.pop("exception", None)

    message = message_of(event)
    if message:
        event["logentry"] = {"formatted": _trim(message)}
    event.pop("message", None)

    crumbs = _values(event.get("breadcrumbs"))[-MAX_BREADCRUMBS:]
    event["breadcrumbs"] = {"values": [{k: _trim(v) for k, v in c.items()} for c in crumbs]}
    event["tags"] = _normalize_tags(event.get("tags"))
    event["request"] = _scrub_request(event.get("request"))
    if event["request"] is None:
        event.pop("request")
    return event
