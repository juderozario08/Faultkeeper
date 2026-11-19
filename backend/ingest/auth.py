"""DSN key authentication and per-key rate limiting for the ingest edge (async)."""

import time
from dataclasses import asdict, dataclass

from django.http import HttpRequest

from organizations.models import ProjectKey

from .store import get_store

KEY_CACHE_TTL = 60


class IngestError(Exception):
    def __init__(self, status: int, detail: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.headers = headers or {}


@dataclass(frozen=True)
class KeyInfo:
    public_key: str
    project_id: int
    is_active: bool
    rate_limit_per_minute: int


def parse_auth_header(value: str) -> dict[str, str]:
    """`Sentry sentry_version=7, sentry_key=abc, sentry_client=x/1.0` -> dict."""
    value = value.strip()
    if value.lower().startswith("sentry "):
        value = value[len("sentry ") :]
    parts: dict[str, str] = {}
    for chunk in value.split(","):
        name, sep, val = chunk.strip().partition("=")
        if sep:
            parts[name.strip()] = val.strip()
    return parts


def extract_public_key(request: HttpRequest) -> str | None:
    header = request.headers.get("X-Sentry-Auth")
    if header:
        key = parse_auth_header(header).get("sentry_key")
        if key:
            return key
    return request.GET.get("sentry_key") or None


async def _load_key(public_key: str) -> KeyInfo | None:
    store = get_store()
    cache_key = f"pk:{public_key}"
    cached = await store.get_json(cache_key)
    if cached is not None:
        return KeyInfo(**cached) if cached else None
    row = await (
        ProjectKey.objects.filter(public_key=public_key)
        .values("public_key", "project_id", "is_active", "rate_limit_per_minute")
        .afirst()
    )
    info = KeyInfo(**row) if row else None
    await store.set_json(cache_key, asdict(info) if info else {}, KEY_CACHE_TTL)  # cache misses too
    return info


async def authenticate(request: HttpRequest, project_id: int) -> KeyInfo:
    public_key = extract_public_key(request)
    if not public_key:
        raise IngestError(401, "missing sentry_key")
    info = await _load_key(public_key)
    if info is None or not info.is_active:
        raise IngestError(401, "invalid or disabled key")
    if info.project_id != project_id:
        raise IngestError(403, "key does not belong to this project")
    return info


async def check_rate_limit(info: KeyInfo, now: float | None = None) -> None:
    """Fixed one-minute window per key."""
    now = time.time() if now is None else now
    minute = int(now // 60)
    count = await get_store().incr_window(f"rl:{info.public_key}:{minute}", ttl=120)
    if count > info.rate_limit_per_minute:
        retry_after = max(1, 60 - int(now % 60))
        raise IngestError(
            429,
            "rate limit exceeded",
            {"Retry-After": str(retry_after), "X-Sentry-Rate-Limits": f"{retry_after}::key"},
        )
