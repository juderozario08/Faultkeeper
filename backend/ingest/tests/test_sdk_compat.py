"""Compatibility with the official Python SDK, using the real `sentry-sdk`.

A custom transport captures the exact envelope bytes the SDK would send over HTTP,
and those bytes are then posted to our ingest endpoint.
"""

from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from django.test import Client
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from issues.models import Event, Group
from organizations.models import ProjectKey


class CapturingTransport(Transport):
    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options)
        self.envelopes: list[bytes] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        self.envelopes.append(envelope.serialize())


@pytest.fixture
def sdk(project_key: ProjectKey) -> Iterator[CapturingTransport]:
    transport = CapturingTransport()
    sentry_sdk.init(
        dsn=project_key.dsn("http://testserver"),
        transport=transport,
        release="shop@1.2.3",
        environment="production",
        default_integrations=False,
    )
    yield transport
    sentry_sdk.get_client().close()


def checkout(cart: dict[str, int]) -> float:
    return cart["total"] / cart["items"]


def deliver(client: Client, key: ProjectKey, transport: CapturingTransport) -> None:
    for body in transport.envelopes:
        response = client.post(
            f"/api/{key.project_id}/envelope/",
            data=body,
            content_type="application/x-sentry-envelope",
            HTTP_X_SENTRY_AUTH=f"Sentry sentry_version=7, sentry_key={key.public_key}",
        )
        assert response.status_code == 200, response.content
    transport.envelopes.clear()


@pytest.mark.django_db
def test_python_sdk_exception_is_grouped(
    client: Client, project_key: ProjectKey, sdk: CapturingTransport
) -> None:
    for _ in range(3):
        try:
            checkout({"total": 10, "items": 0})
        except ZeroDivisionError as exc:
            sentry_sdk.capture_exception(exc)
    sentry_sdk.flush()
    deliver(client, project_key, sdk)

    group = Group.objects.get()
    assert group.title == "ZeroDivisionError: division by zero"
    assert group.times_seen == 3
    assert "checkout" in group.culprit
    event = Event.objects.first()
    assert event is not None
    assert event.release == "shop@1.2.3" and event.environment == "production"
    frame = event.payload["exception"]["values"][0]["stacktrace"]["frames"][-1]
    assert frame["function"] == "checkout"
    assert "cart[" in frame["context_line"]  # the Python SDK sends source context


@pytest.mark.django_db
def test_python_sdk_message(
    client: Client, project_key: ProjectKey, sdk: CapturingTransport
) -> None:
    sentry_sdk.capture_message("Payment provider timed out after 30s", level="warning")
    sentry_sdk.flush()
    deliver(client, project_key, sdk)
    group = Group.objects.get()
    assert group.title == "Payment provider timed out after 30s"
    assert group.level == "warning"
