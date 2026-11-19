import json
from datetime import UTC, datetime
from typing import Any

import pytest
from rest_framework.test import APIClient

from insights import providers
from insights.context import IssueContext, build_context, strip_query
from insights.models import IssueInsight
from issues.models import Group
from organizations.models import OrganizationMember, Project, User
from processing.pipeline import process_event

PAYLOAD: dict[str, Any] = {
    "platform": "python",
    "release": "api@1.0",
    "user": {"email": "secret@example.com", "ip_address": "10.1.2.3"},
    "request": {"url": "https://shop.test/checkout?token=abc", "headers": {"Cookie": "s=1"}},
    "tags": {"browser": "Chrome 130", "user.email": "secret@example.com"},
    "breadcrumbs": [
        {
            "category": "fetch",
            "data": {"method": "POST", "url": "https://api.test/pay?card=4242", "status_code": 500},
        },
        {"category": "console", "message": "retrying https://api.test/x?sig=zzz"},
    ],
    "exception": {
        "values": [
            {
                "type": "ZeroDivisionError",
                "value": "division by zero",
                "stacktrace": {
                    "frames": [
                        {
                            "module": "shop.pricing",
                            "function": "average_rating",
                            "lineno": 7,
                            "in_app": True,
                            "pre_context": ["def average_rating(reviews):"],
                            "context_line": "    return total / len(reviews)",
                            "post_context": [""],
                            "vars": {"reviews": "[]", "password": "hunter2"},
                        }
                    ]
                },
            }
        ]
    },
}


@pytest.fixture
def group(project: Project) -> Group:
    process_event(project.id, dict(PAYLOAD), datetime.now(UTC).isoformat())
    return Group.objects.get()


@pytest.fixture
def api(project: Project) -> APIClient:
    user = User.objects.create_user("dev@example.com", "pw-123456")
    OrganizationMember.objects.create(organization=project.organization, user=user, role="owner")
    client = APIClient()
    client.force_authenticate(user)
    return client


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self, raw: str = "") -> None:
        self.raw = raw or json.dumps({"summary": "S", "root_cause": "R", "suggested_fix": "F"})
        self.prompts: list[str] = []

    def available(self) -> tuple[bool, str]:
        return True, "fake"

    def generate(self, context: Any) -> providers.Insight:
        self.prompts.append(context.to_prompt())
        return providers.parse_insight(self.raw)


@pytest.mark.django_db
def test_context_excludes_pii_vars_and_query_strings(group: Group) -> None:
    prompt = build_context(group, group.events.get().payload).to_prompt()
    assert "average_rating" in prompt and "return total / len(reviews)" in prompt
    for secret in (
        "secret@example.com",
        "10.1.2.3",
        "hunter2",
        "token=abc",
        "card=4242",
        "sig=zzz",
        "s=1",
    ):
        assert secret not in prompt
    assert "https://api.test/pay" in prompt and "browser=Chrome 130" in prompt


def test_strip_query() -> None:
    assert strip_query("https://a.test/p?q=1#frag") == "https://a.test/p"


def test_parse_insight_validates_schema() -> None:
    assert (
        providers.parse_insight('{"summary":"a","root_cause":"b","suggested_fix":"c"}').summary
        == "a"
    )
    for bad in (
        "not json",
        '{"summary":"a"}',
        '{"summary":"","root_cause":"b","suggested_fix":"c"}',
    ):
        with pytest.raises(providers.ProviderError):
            providers.parse_insight(bad)


@pytest.mark.django_db
def test_generate_and_cache(api: APIClient, group: Group, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeProvider()
    monkeypatch.setattr("insights.views.get_provider", lambda: fake)
    assert api.get(f"/api/0/issues/{group.id}/insights/").json()["insight"] is None
    created = api.post(f"/api/0/issues/{group.id}/insights/").json()
    assert created["insight"]["root_cause"] == "R"
    assert api.get(f"/api/0/issues/{group.id}/insights/").json()["insight"]["summary"] == "S"
    assert IssueInsight.objects.count() == 1


@pytest.mark.django_db
def test_bad_model_output_is_502(
    api: APIClient, group: Group, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("insights.views.get_provider", lambda: FakeProvider("nope"))
    assert api.post(f"/api/0/issues/{group.id}/insights/").status_code == 502


@pytest.mark.django_db
def test_disabled_provider_is_503(api: APIClient, group: Group) -> None:
    status = api.get(f"/api/0/issues/{group.id}/insights/").json()
    assert status["available"] is False
    assert api.post(f"/api/0/issues/{group.id}/insights/").status_code == 503


def test_ollama_request_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_post(url: str, body: dict[str, Any], timeout: float, headers: Any = None) -> Any:
        sent.update(url=url, body=body)
        return {"message": {"content": '{"summary":"a","root_cause":"b","suggested_fix":"c"}'}}

    monkeypatch.setattr(providers, "_post_json", fake_post)
    provider = providers.OllamaProvider("http://ollama:11434/", "qwen2.5-coder:3b")
    result = provider.generate(IssueContext("T", "c", "python", "error", 1, None, None))
    assert result.suggested_fix == "c"
    assert sent["url"] == "http://ollama:11434/api/chat"
    assert sent["body"]["format"]["required"] == ["summary", "root_cause", "suggested_fix"]
    assert sent["body"]["stream"] is False


def test_ollama_unreachable_reports_unavailable() -> None:
    available, detail = providers.OllamaProvider("http://127.0.0.1:1", "m").available()
    assert not available and "ollama pull m" in detail
