from typing import Any

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from issues.views import _group_for, latest_event_payload

from .context import build_context
from .models import IssueInsight
from .providers import ProviderError, ProviderUnavailable, get_provider


def _serialize(insight: IssueInsight | None) -> dict[str, Any] | None:
    if insight is None:
        return None
    return {
        "summary": insight.summary,
        "root_cause": insight.root_cause,
        "suggested_fix": insight.suggested_fix,
        "provider": insight.provider,
        "model": insight.model,
        "created_at": insight.created_at.isoformat(),
    }


@api_view(["GET", "POST"])
def issue_insights(request: Request, issue_id: int) -> Response:
    group = _group_for(request, issue_id)
    provider = get_provider()

    if request.method == "GET":
        available, detail = provider.available()
        latest = group.insights.order_by("-created_at").first()
        return Response(
            {"insight": _serialize(latest), "available": available, "provider_detail": detail}
        )

    payload = latest_event_payload(group)
    if payload is None:
        return Response({"detail": "This issue has no events to analyze."}, status=400)
    try:
        result = provider.generate(build_context(group, payload))
    except ProviderUnavailable as exc:
        return Response({"detail": str(exc)}, status=503)
    except ProviderError as exc:
        return Response({"detail": f"The model's answer couldn't be used: {exc}"}, status=502)

    insight = IssueInsight.objects.create(
        group=group,
        provider=provider.name,
        model=provider.model,
        summary=result.summary,
        root_cause=result.root_cause,
        suggested_fix=result.suggested_fix,
    )
    return Response({"insight": _serialize(insight), "available": True, "provider_detail": ""})
