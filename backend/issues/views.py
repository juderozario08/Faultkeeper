from collections import Counter
from typing import Any

from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.pagination import CursorPagination
from rest_framework.request import Request
from rest_framework.response import Response

from organizations.permissions import get_project
from organizations.views import current_user

from . import stats
from .models import Event, Group
from .serializers import (
    EventDetailSerializer,
    EventSummarySerializer,
    GroupSerializer,
    StatusUpdateSerializer,
)

SORTS = {"last_seen": "-last_seen", "first_seen": "-first_seen", "times_seen": "-times_seen"}
TAG_KEYS_FROM_CONTEXTS = {"browser": "browser", "os": "os", "runtime": "runtime"}


class IssuePagination(CursorPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "limit"

    def get_ordering(self, request: Any, queryset: Any, view: Any) -> tuple[str, ...]:
        return (SORTS.get(request.query_params.get("sort", ""), "-last_seen"), "-id")


class EventPagination(CursorPagination):
    page_size = 50
    ordering = ("-timestamp", "-id")


def _group_for(request: Request, issue_id: int) -> Group:
    group = get_object_or_404(Group.objects.select_related("project", "first_release"), pk=issue_id)
    if not group.project.organization.members.filter(user=current_user(request)).exists():
        raise Http404
    return group


def filter_issues(qs: QuerySet[Group], params: Any) -> QuerySet[Group]:
    status = params.get("status", "unresolved")
    if status and status != "all":
        qs = qs.filter(status=status)
    if level := params.get("level"):
        qs = qs.filter(level=level)
    if release := params.get("release"):
        qs = qs.filter(events__release=release)
    if environment := params.get("environment"):
        qs = qs.filter(events__environment=environment)
    if q := params.get("q", "").strip():
        qs = qs.filter(Q(title__icontains=q) | Q(culprit__icontains=q))
    if release or environment:
        qs = qs.distinct()
    return qs


@api_view(["GET"])
def issue_list(request: Request, org_slug: str, project_slug: str) -> Response:
    project = get_project(current_user(request), org_slug, project_slug)
    qs = filter_issues(
        Group.objects.filter(project=project).select_related("project", "first_release"),
        request.query_params,
    )
    paginator = IssuePagination()
    page = paginator.paginate_queryset(qs, request)
    assert page is not None
    sparklines = stats.series(
        project.id, stats.PERIODS["24h"], stats.INTERVALS["1h"], [g.id for g in page]
    )
    data = GroupSerializer(page, many=True).data
    for item in data:
        item["stats_24h"] = sparklines.get(item["id"], [])
    return paginator.get_paginated_response(data)


@api_view(["GET", "PUT"])
def issue_detail(request: Request, issue_id: int) -> Response:
    group = _group_for(request, issue_id)
    if request.method == "PUT":
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        group.status = new_status
        if new_status == Group.Status.RESOLVED:
            group.resolved_at = timezone.now()
        else:
            group.resolved_at = None
            group.substatus = Group.Substatus.ONGOING
        group.save(update_fields=["status", "substatus", "resolved_at"])
        _broadcast(group)
    data = GroupSerializer(group).data
    data["stats_24h"] = stats.series(
        group.project_id, stats.PERIODS["24h"], stats.INTERVALS["1h"], [group.id]
    )[group.id]
    return Response(data)


def _broadcast(group: Group) -> None:
    from realtime.publish import publish_group_update

    publish_group_update(group, created=False)


@api_view(["GET"])
def issue_events(request: Request, issue_id: int) -> Response:
    group = _group_for(request, issue_id)
    paginator = EventPagination()
    page = paginator.paginate_queryset(group.events.all(), request)
    assert page is not None
    return paginator.get_paginated_response(EventSummarySerializer(page, many=True).data)


@api_view(["GET"])
def issue_event_detail(request: Request, issue_id: int, event_id: str) -> Response:
    """`event_id` may be a hex id, `latest`, or `oldest`. Includes prev/next ids."""
    group = _group_for(request, issue_id)
    events = group.events.order_by("-timestamp", "-id")
    if event_id == "latest":
        event = events.first()
    elif event_id == "oldest":
        event = events.last()
    else:
        try:
            event = events.filter(event_id=event_id).first()
        except Exception as exc:  # malformed uuid
            raise Http404 from exc
    if event is None:
        raise Http404

    newer = (
        group.events.filter(
            Q(timestamp__gt=event.timestamp) | Q(timestamp=event.timestamp, id__gt=event.id)
        )
        .order_by("timestamp", "id")
        .first()
    )
    older = (
        group.events.filter(
            Q(timestamp__lt=event.timestamp) | Q(timestamp=event.timestamp, id__lt=event.id)
        )
        .order_by("-timestamp", "-id")
        .first()
    )

    data = EventDetailSerializer(event).data
    data["next_event_id"] = newer.event_id.hex if newer else None
    data["previous_event_id"] = older.event_id.hex if older else None
    return Response(data)


def _event_tags(payload: dict[str, Any]) -> list[tuple[str, str]]:
    tags = [(str(k), str(v)) for k, v in payload.get("tags") or []]
    contexts = payload.get("contexts") or {}
    present = {k for k, _ in tags}
    for tag, ctx_key in TAG_KEYS_FROM_CONTEXTS.items():
        ctx = contexts.get(ctx_key)
        if tag not in present and isinstance(ctx, dict) and ctx.get("name"):
            version = ctx.get("version")
            tags.append((tag, f"{ctx['name']} {version}".strip() if version else ctx["name"]))
    for key in ("release", "environment", "level"):
        if payload.get(key) and key not in present:
            tags.append((key, str(payload[key])))
    return tags


@api_view(["GET"])
def issue_tags(request: Request, issue_id: int) -> Response:
    """Top tag values over the issue's most recent 500 events."""
    group = _group_for(request, issue_id)
    counters: dict[str, Counter[str]] = {}
    sample = group.events.order_by("-timestamp").values_list("payload", flat=True)[:500]
    for payload in sample:
        for key, value in _event_tags(payload):
            counters.setdefault(key, Counter())[value] += 1
    return Response(
        [
            {
                "key": key,
                "total": sum(counter.values()),
                "top": [{"value": v, "count": c} for v, c in counter.most_common(5)],
            }
            for key, counter in sorted(counters.items())
        ]
    )


@api_view(["GET"])
def project_stats(request: Request, org_slug: str, project_slug: str) -> Response:
    project = get_project(current_user(request), org_slug, project_slug)
    period = stats.PERIODS.get(request.query_params.get("period", "24h"), stats.PERIODS["24h"])
    interval = stats.INTERVALS.get(
        request.query_params.get("interval", "1h"), stats.INTERVALS["1h"]
    )
    return Response(stats.series(project.id, period, interval)[None])


@api_view(["GET"])
def project_filters(request: Request, org_slug: str, project_slug: str) -> Response:
    """Values for the issue-list filter dropdowns."""
    project = get_project(current_user(request), org_slug, project_slug)
    return Response(
        {
            "releases": list(
                project.releases.order_by("-first_seen").values_list("version", flat=True)[:50]
            ),
            "environments": list(
                project.environments.order_by("name").values_list("name", flat=True)
            ),
        }
    )


def latest_event_payload(group: Group) -> dict[str, Any] | None:
    event: Event | None = group.events.order_by("-timestamp").first()
    return event.payload if event else None
