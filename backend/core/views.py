from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse


def _check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _check_cache() -> bool:
    try:
        cache.set("health:ping", "pong", timeout=5)
        return cache.get("health:ping") == "pong"
    except Exception:
        return False


def health(request: HttpRequest) -> JsonResponse:
    """Liveness/readiness probe. Public, no auth."""
    checks = {"database": _check_database(), "cache": _check_cache()}
    ok = all(checks.values())
    return JsonResponse(
        {"status": "ok" if ok else "degraded", "mode": settings.DEPLOY_MODE, "checks": checks},
        status=200 if ok else 503,
    )
