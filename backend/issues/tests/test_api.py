from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from rest_framework.test import APIClient

from issues.models import Group
from organizations.models import Organization, OrganizationMember, Project, User
from processing.pipeline import process_event


def send(project: Project, type_: str = "TypeError", fn: str = "checkout", **extra: Any) -> None:
    payload = {
        "platform": "javascript",
        "exception": {
            "values": [
                {
                    "type": type_,
                    "value": "boom",
                    "stacktrace": {"frames": [{"filename": "src/app.ts", "function": fn}]},
                }
            ]
        },
        "contexts": {"browser": {"name": "Chrome", "version": "130"}},
        "tags": {"page": "/cart"},
        **extra,
    }
    process_event(project.id, payload, datetime.now(UTC).isoformat())


@pytest.fixture
def api(project: Project) -> APIClient:
    user = User.objects.create_user("dev@example.com", "pw-123456")
    OrganizationMember.objects.create(organization=project.organization, user=user, role="owner")
    client = APIClient()
    client.force_authenticate(user)
    return client


def issues_url(project: Project) -> str:
    return f"/api/0/projects/{project.organization.slug}/{project.slug}/issues/"


@pytest.mark.django_db
def test_issue_list_with_sparklines(api: APIClient, project: Project) -> None:
    send(project)
    send(project)
    send(project, fn="applyCoupon")
    body = api.get(issues_url(project)).json()
    assert len(body["results"]) == 2
    top = max(body["results"], key=lambda i: i["times_seen"])
    assert top["times_seen"] == 2
    assert len(top["stats_24h"]) == 24
    assert sum(c for _, c in top["stats_24h"]) == 2


@pytest.mark.django_db
def test_issue_list_filters(api: APIClient, project: Project) -> None:
    send(project, release="1.0", environment="prod", level="warning")
    send(project, type_="RangeError", release="2.0", environment="staging")
    url = issues_url(project)
    assert len(api.get(url, {"release": "1.0"}).json()["results"]) == 1
    assert len(api.get(url, {"environment": "staging"}).json()["results"]) == 1
    assert len(api.get(url, {"level": "warning"}).json()["results"]) == 1
    assert len(api.get(url, {"q": "rangeerror"}).json()["results"]) == 1
    Group.objects.filter(title__startswith="RangeError").update(status="resolved")
    assert len(api.get(url).json()["results"]) == 1  # default: unresolved
    assert len(api.get(url, {"status": "all"}).json()["results"]) == 2


@pytest.mark.django_db
def test_sort_and_pagination(api: APIClient, project: Project) -> None:
    for i in range(30):
        send(project, fn=f"fn{i}")
    send(project, fn="fn3")
    first = api.get(issues_url(project), {"sort": "times_seen"}).json()
    assert first["results"][0]["times_seen"] == 2
    assert len(first["results"]) == 25 and first["next"]
    second = api.get(first["next"]).json()
    assert len(second["results"]) == 5


@pytest.mark.django_db
def test_resolve_and_reopen(api: APIClient, project: Project) -> None:
    send(project)
    group = Group.objects.get()
    resolved = api.put(f"/api/0/issues/{group.id}/", {"status": "resolved"}, format="json")
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    assert (
        api.put(f"/api/0/issues/{group.id}/", {"status": "bogus"}, format="json").status_code == 400
    )
    send(project)  # regression
    assert api.get(f"/api/0/issues/{group.id}/").json()["substatus"] == "regressed"


@pytest.mark.django_db
def test_events_navigation_and_tags(api: APIClient, project: Project) -> None:
    for _ in range(3):
        send(project)
    group = Group.objects.get()
    events = api.get(f"/api/0/issues/{group.id}/events/").json()["results"]
    assert len(events) == 3
    latest = api.get(f"/api/0/issues/{group.id}/events/latest/").json()
    assert latest["payload"]["exception"]["values"][0]["type"] == "TypeError"
    assert latest["next_event_id"] is None and latest["previous_event_id"]
    older = api.get(f"/api/0/issues/{group.id}/events/{latest['previous_event_id']}/").json()
    assert older["next_event_id"] == latest["event_id"]
    tags = {t["key"]: t for t in api.get(f"/api/0/issues/{group.id}/tags/").json()}
    assert tags["browser"]["top"][0] == {"value": "Chrome 130", "count": 3}
    assert tags["page"]["top"][0]["value"] == "/cart"


@pytest.mark.django_db
def test_project_stats_and_filters(api: APIClient, project: Project) -> None:
    send(project, release="1.0", environment="prod")
    base = f"/api/0/projects/{project.organization.slug}/{project.slug}"
    series = api.get(f"{base}/stats/", {"period": "7d", "interval": "1d"}).json()
    assert len(series) == 7 and series[-1][1] == 1
    assert api.get(f"{base}/filters/").json() == {"releases": ["1.0"], "environments": ["prod"]}


@pytest.mark.django_db
def test_other_orgs_issues_are_hidden(api: APIClient, project: Project) -> None:
    other_org = Organization.objects.create(name="Other", slug="other")
    other = Project.objects.create(organization=other_org, name="X", slug="x")
    send(other)
    group = Group.objects.get()
    assert api.get(f"/api/0/issues/{group.id}/").status_code == 404
    assert api.get(issues_url(other)).status_code == 404


def test_buckets_are_contiguous() -> None:
    from issues.stats import buckets

    now = datetime(2026, 11, 18, 12, 34, tzinfo=UTC)
    slots = buckets(timedelta(hours=24), timedelta(hours=1), now)
    assert len(slots) == 24 and slots[-1] == datetime(2026, 11, 18, 12, tzinfo=UTC)
