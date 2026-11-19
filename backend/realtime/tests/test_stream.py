from datetime import UTC, datetime

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from organizations.models import Organization, OrganizationMember, Project, User
from processing.pipeline import process_event
from realtime.routing import websocket_urlpatterns

app = URLRouter(websocket_urlpatterns)


def make_project_and_user() -> tuple[Project, User]:
    org = Organization.objects.create(name="Acme", slug="acme")
    project = Project.objects.create(organization=org, name="Web", slug="web")
    user = User.objects.create_user("dev@example.com", "pw-123456")
    OrganizationMember.objects.create(organization=org, user=user, role="member")
    return project, user


def send_event(project_id: int) -> None:
    process_event(
        project_id,
        {"exception": {"values": [{"type": "TypeError", "value": "boom"}]}},
        datetime.now(UTC).isoformat(),
    )


def connect(project_id: int, user: object) -> WebsocketCommunicator:
    communicator = WebsocketCommunicator(app, f"/ws/projects/{project_id}/")
    communicator.scope["user"] = user
    return communicator


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_member_receives_created_then_updated() -> None:
    project, user = await sync_to_async(make_project_and_user)()
    ws = connect(project.id, user)
    connected, _ = await ws.connect()
    assert connected

    await sync_to_async(send_event)(project.id)
    created = await ws.receive_json_from(timeout=2)
    assert created["type"] == "issue.created"
    assert created["issue"]["title"] == "TypeError: boom"

    await sync_to_async(send_event)(project.id)
    updated = await ws.receive_json_from(timeout=2)
    assert updated["type"] == "issue.updated"
    assert updated["issue"]["times_seen"] == 2
    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_anonymous_and_non_members_are_rejected() -> None:
    project, _ = await sync_to_async(make_project_and_user)()
    outsider = await sync_to_async(User.objects.create_user)("x@example.com", "pw-123456")

    for user in (AnonymousUser(), outsider):
        ws = connect(project.id, user)
        connected, code = await ws.connect()
        assert not connected and code == 4403
