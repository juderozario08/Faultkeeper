import pytest
from django.test import Client, override_settings

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@pytest.mark.django_db
@override_settings(CACHES=LOCMEM)
def test_health_ok(client: Client) -> None:
    response = client.get("/api/0/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": True, "cache": True}


@pytest.mark.django_db
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://127.0.0.1:1/0",  # nothing listens here
        }
    }
)
def test_health_reports_degraded_when_cache_down(client: Client) -> None:
    response = client.get("/api/0/health/")
    assert response.status_code == 503
    assert response.json()["checks"]["cache"] is False
