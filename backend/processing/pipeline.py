"""The event pipeline: normalize -> fingerprint -> group -> save -> broadcast.

`process_event` doesn't depend on the transport, so Celery, Kafka, and the
in-process worker all call this same function (ADR 0004).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest

from issues.models import Environment, Event, Group, GroupHash, Release

from .grouping import event_culprit, event_title, grouping_hash, is_message_event
from .normalize import normalize

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    event: Event
    group: Group
    is_new_group: bool
    is_regression: bool
    is_duplicate: bool = False


def _release(project_id: int, version: str | None, seen: datetime) -> Release | None:
    if not version:
        return None
    release, _ = Release.objects.get_or_create(
        project_id=project_id, version=version, defaults={"first_seen": seen}
    )
    return release


def _get_or_create_group(
    project_id: int, hash_: str, data: dict[str, Any], ts: datetime, release: Release | None
) -> tuple[Group, bool]:
    existing = GroupHash.objects.select_related("group").filter(project_id=project_id, hash=hash_)
    found = existing.first()
    if found:
        return found.group, False
    try:
        with transaction.atomic():
            group = Group.objects.create(
                project_id=project_id,
                title=event_title(data),
                culprit=event_culprit(data),
                type="default" if is_message_event(data) else "error",
                level=data["level"],
                platform=data["platform"],
                first_seen=ts,
                last_seen=ts,
                times_seen=0,  # incremented with every event, including this one
                first_release=release,
            )
            GroupHash.objects.create(project_id=project_id, hash=hash_, group=group)
            return group, True
    except IntegrityError:
        # Another worker created the same group concurrently.
        return GroupHash.objects.select_related("group").get(
            project_id=project_id, hash=hash_
        ).group, False


def process_event(project_id: int, payload: dict[str, Any], received_at: str) -> ProcessResult:
    received = datetime.fromisoformat(received_at)
    data = normalize(payload, received)
    ts = datetime.fromisoformat(data["timestamp"])

    duplicate = Event.objects.filter(project_id=project_id, event_id=data["event_id"]).first()
    if duplicate:
        return ProcessResult(duplicate, duplicate.group, False, False, is_duplicate=True)

    hash_ = grouping_hash(data)
    try:
        with transaction.atomic():
            release = _release(project_id, data.get("release"), ts)
            if data.get("environment"):
                Environment.objects.get_or_create(project_id=project_id, name=data["environment"])

            group, is_new = _get_or_create_group(project_id, hash_, data, ts, release)

            is_regression = bool(
                Group.objects.filter(pk=group.pk, status=Group.Status.RESOLVED).update(
                    status=Group.Status.UNRESOLVED,
                    substatus=Group.Substatus.REGRESSED,
                    resolved_at=None,
                )
            )
            Group.objects.filter(pk=group.pk).update(
                times_seen=F("times_seen") + 1,
                last_seen=Greatest(F("last_seen"), Value(ts)),
            )

            event = Event.objects.create(
                event_id=data["event_id"],
                project_id=project_id,
                group=group,
                timestamp=ts,
                received_at=received,
                level=data["level"],
                platform=data["platform"],
                release=data.get("release") or "",
                environment=data.get("environment") or "",
                title=event_title(data),
                payload=data,
            )
    except IntegrityError:
        # Same event_id delivered twice concurrently (at-least-once delivery).
        duplicate = Event.objects.get(project_id=project_id, event_id=data["event_id"])
        return ProcessResult(duplicate, duplicate.group, False, False, is_duplicate=True)

    group.refresh_from_db()
    result = ProcessResult(event, group, is_new, is_regression)
    transaction.on_commit(lambda: _broadcast(result))
    return result


def _broadcast(result: ProcessResult) -> None:
    try:
        from realtime.publish import publish_group_update

        publish_group_update(result.group, created=result.is_new_group)
    except Exception:  # realtime must never break ingestion
        logger.exception("failed to broadcast group update")
