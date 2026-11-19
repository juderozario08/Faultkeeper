"""Fast key/value operations for the ingest hot path.

Django's cache API (even its `a*` methods) funnels through one shared sync thread
under ASGI, which serialises every ingest request. In standard mode we talk to
Redis with a native asyncio client instead; elsewhere (tests, single mode) we fall
back to Django's cache in a non-thread-sensitive executor.
"""

import json
from typing import Any, Protocol

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache


class IngestStore(Protocol):
    async def get_json(self, key: str) -> Any: ...

    async def set_json(self, key: str, value: Any, ttl: int) -> None: ...

    async def incr_window(self, key: str, ttl: int) -> int: ...


class RedisStore:
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url)

    async def get_json(self, key: str) -> Any:
        raw = await self._redis.get(f"ingest:{key}")
        return None if raw is None else json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        await self._redis.set(f"ingest:{key}", json.dumps(value), ex=ttl)

    async def incr_window(self, key: str, ttl: int) -> int:
        pipe = self._redis.pipeline(transaction=True)
        pipe.incr(f"ingest:{key}")
        pipe.expire(f"ingest:{key}", ttl, nx=True)
        count, _ = await pipe.execute()
        return int(count)


class CacheStore:
    async def get_json(self, key: str) -> Any:
        return await sync_to_async(cache.get, thread_sensitive=False)(key)

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        await sync_to_async(cache.set, thread_sensitive=False)(key, value, ttl)

    async def incr_window(self, key: str, ttl: int) -> int:
        def incr() -> int:
            cache.add(key, 0, timeout=ttl)
            try:
                return int(cache.incr(key))
            except ValueError:  # expired between add and incr
                cache.set(key, 1, timeout=ttl)
                return 1

        return await sync_to_async(incr, thread_sensitive=False)()


_store: IngestStore | None = None


def get_store() -> IngestStore:
    global _store
    if _store is None:
        backend = settings.CACHES["default"]["BACKEND"]
        _store = RedisStore(settings.REDIS_URL) if backend.endswith("RedisCache") else CacheStore()
    return _store


def reset_store() -> None:
    """Testing hook: forget the cached store (e.g. after settings change)."""
    global _store
    _store = None
