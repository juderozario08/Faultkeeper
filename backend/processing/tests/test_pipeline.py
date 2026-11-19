from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from issues.models import Environment, Event, Group, Release
from issues.tasks import cleanup_old_events
from organizations.models import Project
from processing.normalize import normalize
from processing.pipeline import process_event

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def payload(**extra: Any) -> dict[str, Any]:
    return {
        "level": "error",
        "platform": "javascript",
        "exception": {
            "values": [
                {
                    "type": "TypeError",
                    "value": "x is undefined",
                    "stacktrace": {
                        "frames": [{"filename": "src/Cart.tsx", "function": "checkout"}]
                    },
                }
            ]
        },
        **extra,
    }


def run(project: Project, **extra: Any):
    return process_event(project.id, payload(**extra), NOW.isoformat())


@pytest.mark.django_db
def test_events_group_and_count(project: Project) -> None:
    first = run(project, timestamp=(NOW - timedelta(minutes=5)).timestamp())
    second = run(project)
    assert first.is_new_group and not second.is_new_group
    group = Group.objects.get()
    assert group.times_seen == 2
    assert group.last_seen == NOW
    assert group.first_seen == NOW - timedelta(minutes=5)
    assert Event.objects.count() == 2


@pytest.mark.django_db
def test_duplicate_event_id_is_idempotent(project: Project) -> None:
    event_id = "9ec79c33ec9942ab8353589fcb2e04dc"
    run(project, event_id=event_id)
    again = run(project, event_id=event_id)
    assert again.is_duplicate
    assert Event.objects.count() == 1
    assert Group.objects.get().times_seen == 1


@pytest.mark.django_db
def test_regression_reopens_resolved_issue(project: Project) -> None:
    run(project)
    Group.objects.update(status=Group.Status.RESOLVED, resolved_at=NOW)
    result = run(project)
    group = Group.objects.get()
    assert result.is_regression
    assert group.status == Group.Status.UNRESOLVED
    assert group.substatus == Group.Substatus.REGRESSED


@pytest.mark.django_db
def test_release_and_environment_recorded(project: Project) -> None:
    run(project, release="shop@1.0.0", environment="staging")
    run(project, release="shop@1.0.0", environment="staging")
    assert Release.objects.get().version == "shop@1.0.0"
    assert Environment.objects.get().name == "staging"
    assert Group.objects.get().first_release is not None


@pytest.mark.django_db
def test_retention_deletes_old_events_only(project: Project) -> None:
    run(project, timestamp=(datetime.now(UTC) - timedelta(days=40)).timestamp())
    process_event(project.id, payload(), datetime.now(UTC).isoformat())
    assert cleanup_old_events() == 1
    assert Event.objects.count() == 1
    assert Group.objects.count() == 1


def test_normalize_scrubs_and_bounds() -> None:
    data = normalize(
        {
            "event_id": "not-a-uuid",
            "timestamp": (NOW + timedelta(hours=1)).isoformat(),  # future -> clamped
            "level": "LOUD",
            "message": "hello",
            "request": {
                "headers": {"Authorization": "Bearer x", "Accept": "*/*"},
                "cookies": "a=b",
            },
            "tags": {"browser": "Chrome"},
            "breadcrumbs": [{"message": str(i)} for i in range(150)],
        },
        NOW,
    )
    assert len(data["event_id"]) == 32
    assert data["timestamp"] == NOW.isoformat()
    assert data["level"] == "error"
    assert data["logentry"] == {"formatted": "hello"}
    assert data["request"]["headers"]["Authorization"] == "[Filtered]"
    assert "cookies" not in data["request"]
    assert data["tags"] == [["browser", "Chrome"]]
    assert len(data["breadcrumbs"]["values"]) == 100


def test_normalize_marks_library_frames() -> None:
    data = normalize(
        {
            "exception": {
                "values": [
                    {
                        "type": "E",
                        "stacktrace": {
                            "frames": [
                                {"abs_path": "/usr/lib/python3.12/site-packages/django/core.py"},
                                {"abs_path": "/app/shop/views.py"},
                            ]
                        },
                    }
                ]
            }
        },
        NOW,
    )
    frames = data["exception"]["values"][0]["stacktrace"]["frames"]
    assert [f["in_app"] for f in frames] == [False, True]


def test_native_frames_are_never_in_app() -> None:
    data = normalize(
        {
            "exception": {
                "values": [
                    {
                        "type": "TypeError",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "http://localhost:5174/src/main.ts",
                                    "function": "cartTotal",
                                    "in_app": True,
                                },
                                {
                                    "filename": "<anonymous>",
                                    "function": "Array.reduce",
                                    "in_app": True,
                                },
                            ]
                        },
                    }
                ]
            }
        },
        NOW,
    )
    frames = data["exception"]["values"][0]["stacktrace"]["frames"]
    assert [f["in_app"] for f in frames] == [True, False]
