import gzip
import json
import zlib
from typing import Any

import brotli
import pytest
from django.test import Client, override_settings

from issues.models import Event, Group
from organizations.models import ProjectKey

from ..auth import parse_auth_header

EVENT = {
    "event_id": "9ec79c33ec9942ab8353589fcb2e04dc",
    "level": "error",
    "platform": "python",
    "exception": {"values": [{"type": "ValueError", "value": "bad"}]},
}


def envelope(event: dict = EVENT) -> bytes:
    payload = json.dumps(event).encode()
    return (
        b"{}\n" + json.dumps({"type": "event", "length": len(payload)}).encode() + b"\n" + payload
    )


def post(client: Client, project_id: int, body: bytes, key: str | None, **extra: Any) -> Any:
    url = f"/api/{project_id}/envelope/"
    if key:
        url += f"?sentry_key={key}&sentry_version=7"
    return client.post(url, data=body, content_type="text/plain;charset=UTF-8", **extra)


def test_parse_auth_header() -> None:
    parsed = parse_auth_header("Sentry sentry_version=7, sentry_key=abc, sentry_client=x/1.0")
    assert parsed == {"sentry_version": "7", "sentry_key": "abc", "sentry_client": "x/1.0"}


@pytest.mark.django_db
def test_accepts_event_and_processes_it(client: Client, project_key: ProjectKey) -> None:
    response = post(client, project_key.project_id, envelope(), project_key.public_key)
    assert response.status_code == 200
    assert response.json() == {"id": EVENT["event_id"]}
    assert response["Access-Control-Allow-Origin"] == "*"
    assert Event.objects.count() == 1
    assert Group.objects.get().title == "ValueError: bad"


@pytest.mark.django_db
def test_auth_header_also_works(client: Client, project_key: ProjectKey) -> None:
    response = post(
        client,
        project_key.project_id,
        envelope(),
        key=None,
        HTTP_X_SENTRY_AUTH=f"Sentry sentry_version=7, sentry_key={project_key.public_key}",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_auth_failures(client: Client, project_key: ProjectKey) -> None:
    pid = project_key.project_id
    assert post(client, pid, envelope(), None).status_code == 401
    assert post(client, pid, envelope(), "f" * 32).status_code == 401
    assert post(client, pid + 99, envelope(), project_key.public_key).status_code == 403
    ProjectKey.objects.filter(pk=project_key.pk).update(is_active=False)
    from django.core.cache import cache

    cache.clear()
    assert post(client, pid, envelope(), project_key.public_key).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "encoding,compress",
    [
        ("gzip", gzip.compress),
        ("deflate", zlib.compress),
        ("br", brotli.compress),
    ],
)
def test_compressed_bodies(client: Client, project_key: ProjectKey, encoding, compress) -> None:
    response = post(
        client,
        project_key.project_id,
        compress(envelope()),
        project_key.public_key,
        HTTP_CONTENT_ENCODING=encoding,
    )
    assert response.status_code == 200, response.content
    assert Event.objects.count() == 1


@pytest.mark.django_db
@override_settings(INGEST_MAX_BYTES=200)
def test_too_large_after_decompression(client: Client, project_key: ProjectKey) -> None:
    big = envelope({**EVENT, "extra": {"blob": "x" * 5000}})
    response = post(
        client,
        project_key.project_id,
        gzip.compress(big),
        project_key.public_key,
        HTTP_CONTENT_ENCODING="gzip",
    )
    assert response.status_code == 413
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_rate_limit(client: Client, project_key: ProjectKey) -> None:
    ProjectKey.objects.filter(pk=project_key.pk).update(rate_limit_per_minute=2)
    statuses = [
        post(
            client,
            project_key.project_id,
            envelope({**EVENT, "event_id": None}),
            project_key.public_key,
        ).status_code
        for _ in range(3)
    ]
    assert statuses[:2] == [200, 200]
    limited = post(client, project_key.project_id, envelope(), project_key.public_key)
    assert limited.status_code == 429
    assert int(limited["Retry-After"]) >= 1
    assert limited["X-Sentry-Rate-Limits"].endswith("::key")


@pytest.mark.django_db
def test_malformed_envelope_is_400(client: Client, project_key: ProjectKey) -> None:
    response = post(client, project_key.project_id, b"{}\n{}\n", project_key.public_key)
    assert response.status_code == 400


@pytest.mark.django_db
def test_non_event_items_are_acknowledged_and_dropped(
    client: Client, project_key: ProjectKey
) -> None:
    body = b'{"event_id":"9ec79c33ec9942ab8353589fcb2e04dc"}\n{"type":"session"}\n{"sid":"x"}\n'
    response = post(client, project_key.project_id, body, project_key.public_key)
    assert response.status_code == 200
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_options_preflight(client: Client, project_key: ProjectKey) -> None:
    response = client.options(f"/api/{project_key.project_id}/envelope/")
    assert response.status_code == 200
    assert "X-Sentry-Auth" in response["Access-Control-Allow-Headers"]


@pytest.mark.django_db
def test_store_endpoint(client: Client, project_key: ProjectKey) -> None:
    response = client.post(
        f"/api/{project_key.project_id}/store/?sentry_key={project_key.public_key}",
        data=json.dumps(EVENT),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert Event.objects.count() == 1
