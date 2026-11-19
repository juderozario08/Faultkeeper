"""Time-series counts from Postgres (ClickHouse replaces this in phase 2)."""

from collections import Counter
from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncHour
from django.utils import timezone

from .models import Event

INTERVALS = {"1h": timedelta(hours=1), "1d": timedelta(days=1)}
PERIODS = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "14d": timedelta(days=14)}


def _floor(moment: datetime, interval: timedelta) -> datetime:
    if interval >= timedelta(days=1):
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return moment.replace(minute=0, second=0, microsecond=0)


def buckets(period: timedelta, interval: timedelta, now: datetime | None = None) -> list[datetime]:
    end = _floor(now or timezone.now(), interval)
    count = int(period / interval)
    return [end - interval * i for i in range(count - 1, -1, -1)]


def series(
    project_id: int,
    period: timedelta,
    interval: timedelta,
    group_ids: list[int] | None = None,
) -> dict[int | None, list[list[int]]]:
    """Return `{group_id or None: [[unix_ts, count], ...]}` with zero-filled buckets."""
    slots = buckets(period, interval)
    trunc = TruncDay if interval >= timedelta(days=1) else TruncHour
    qs = Event.objects.filter(project_id=project_id, timestamp__gte=slots[0])
    if group_ids is not None:
        qs = qs.filter(group_id__in=group_ids)
        rows = qs.annotate(b=trunc("timestamp")).values("group_id", "b").annotate(n=Count("id"))
        per_group: dict[int, Counter[datetime]] = {gid: Counter() for gid in group_ids}
        for row in rows:
            per_group[row["group_id"]][row["b"]] += row["n"]
        return {
            gid: [[int(s.timestamp()), counts.get(s, 0)] for s in slots]
            for gid, counts in per_group.items()
        }
    totals: Counter[datetime] = Counter()
    for total in qs.annotate(b=trunc("timestamp")).values("b").annotate(n=Count("id")):
        totals[total["b"]] += total["n"]
    return {None: [[int(s.timestamp()), totals.get(s, 0)] for s in slots]}
