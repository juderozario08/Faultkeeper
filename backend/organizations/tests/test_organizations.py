import re

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from organizations.models import Organization, OrganizationMember, Project, ProjectKey, User


@pytest.fixture
def user() -> User:
    return User.objects.create_user("dev@example.com", "pw-123456", name="Dev")


@pytest.fixture
def org(user: User) -> Organization:
    org = Organization.objects.create(name="Acme", slug="acme")
    OrganizationMember.objects.create(organization=org, user=user, role="owner")
    return org


@pytest.fixture
def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_public_key_is_32_hex() -> None:
    org = Organization.objects.create(name="A", slug="a")
    key = ProjectKey.objects.create(
        project=Project.objects.create(organization=org, name="P", slug="p")
    )
    assert re.fullmatch(r"[0-9a-f]{32}", key.public_key)


@pytest.mark.django_db
def test_dsn_format(org: Organization) -> None:
    project = Project.objects.create(organization=org, name="Web", slug="web")
    key = ProjectKey.objects.create(project=project, public_key="a" * 32)
    assert (
        key.dsn("https://errors.example.com")
        == f"https://{'a' * 32}@errors.example.com/{project.id}"
    )


@pytest.mark.django_db
def test_login_me_logout() -> None:
    User.objects.create_user("Dev@Example.com", "pw-123456")
    client = APIClient()
    assert client.get("/api/0/auth/me/").status_code == 403
    bad = client.post("/api/0/auth/login/", {"email": "dev@example.com", "password": "nope"})
    assert bad.status_code == 400
    ok = client.post("/api/0/auth/login/", {"email": "DEV@example.com", "password": "pw-123456"})
    assert ok.status_code == 200
    assert client.get("/api/0/auth/me/").json()["email"] == "dev@example.com"
    assert client.post("/api/0/auth/logout/").status_code == 204
    assert client.get("/api/0/auth/me/").status_code == 403


@pytest.mark.django_db
def test_org_and_project_listing_is_scoped(api: APIClient, org: Organization) -> None:
    other = Organization.objects.create(name="Other", slug="other")
    Project.objects.create(organization=other, name="Secret", slug="secret")
    Project.objects.create(organization=org, name="Web", slug="web")

    assert [o["slug"] for o in api.get("/api/0/organizations/").json()] == ["acme"]
    assert [p["slug"] for p in api.get("/api/0/organizations/acme/projects/").json()] == ["web"]
    assert api.get("/api/0/organizations/other/projects/").status_code == 404
    assert api.get("/api/0/projects/other/secret/keys/").status_code == 404


@pytest.mark.django_db
def test_create_project_creates_key_and_respects_role(
    api: APIClient, org: Organization, user: User
) -> None:
    created = api.post("/api/0/organizations/acme/projects/", {"name": "Api", "slug": "api"})
    assert created.status_code == 201
    keys = api.get("/api/0/projects/acme/api/keys/").json()
    assert len(keys) == 1 and keys[0]["dsn"].endswith(f"/{created.json()['id']}")

    OrganizationMember.objects.filter(user=user).update(role="member")
    denied = api.post("/api/0/organizations/acme/projects/", {"name": "X", "slug": "x"})
    assert denied.status_code == 403


@pytest.mark.django_db
def test_seed_demo_is_idempotent() -> None:
    call_command("seed_demo")
    call_command("seed_demo")
    assert User.objects.count() == 1
    assert Project.objects.filter(organization__slug="demo").count() == 3
    assert ProjectKey.objects.count() == 3


@pytest.mark.django_db
def test_reset_demo_keeps_projects_and_keys() -> None:
    from datetime import UTC, datetime

    from issues.models import Event, Group
    from processing.pipeline import process_event

    call_command("seed_demo")
    project = Project.objects.get(slug="buggy-shop")
    process_event(project.id, {"message": "hello"}, datetime.now(UTC).isoformat())
    assert Group.objects.count() == 1
    call_command("reset_demo")
    assert Group.objects.count() == 0 and Event.objects.count() == 0
    assert ProjectKey.objects.count() == 3
