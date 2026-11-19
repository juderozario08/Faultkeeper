"""LLM providers for Issue Insights (ADR 0008). All free: local Ollama or Gemini's free tier."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings

from .context import IssueContext

SYSTEM_PROMPT = (
    "You are a senior software engineer helping a developer debug a production error "
    "reported to an error-tracking tool. Using only the evidence provided (exception, stack "
    "frames with source code, breadcrumbs, tags), explain what went wrong. Be concrete: name "
    "the function and line, the bad value or state, and how it got there. If the evidence is "
    "insufficient, say what is missing. Keep each field under 120 words. Respond as JSON."
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One or two sentences: what happened."},
        "root_cause": {"type": "string", "description": "Why it happened, citing code/frames."},
        "suggested_fix": {"type": "string", "description": "Concrete change to fix it."},
    },
    "required": ["summary", "root_cause", "suggested_fix"],
}


class ProviderUnavailable(Exception):
    """The provider is disabled, unreachable, or misconfigured."""


class ProviderError(Exception):
    """The provider responded, but not with a usable answer."""


@dataclass
class Insight:
    summary: str
    root_cause: str
    suggested_fix: str


class InsightProvider(Protocol):
    name: str
    model: str

    def available(self) -> tuple[bool, str]: ...

    def generate(self, context: IssueContext) -> Insight: ...


def parse_insight(raw: str) -> Insight:
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ProviderError("model did not return JSON") from exc
    if not isinstance(data, dict) or not all(
        isinstance(data.get(k), str) and data[k].strip() for k in SCHEMA["required"]
    ):
        raise ProviderError("model output did not match the schema")
    return Insight(
        summary=data["summary"].strip(),
        root_cause=data["root_cause"].strip(),
        suggested_fix=data["suggested_fix"].strip(),
    )


def _post_json(
    url: str, body: dict[str, Any], timeout: float, headers: dict[str, str] | None = None
) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (fixed URLs)
        return json.loads(response.read())


class DisabledProvider:
    name = "disabled"
    model = ""

    def available(self) -> tuple[bool, str]:
        return False, "Issue Insights is turned off (INSIGHTS_PROVIDER=disabled)."

    def generate(self, context: IssueContext) -> Insight:
        raise ProviderUnavailable(self.available()[1])


class OllamaProvider:
    """Local models via Ollama's HTTP API, with JSON-schema structured output."""

    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def available(self) -> tuple[bool, str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as response:  # noqa: S310
                models = {m.get("name") for m in json.loads(response.read()).get("models", [])}
        except (urllib.error.URLError, OSError, ValueError):
            return False, (
                f"Ollama isn't reachable at {self.base_url}. Install it from ollama.com and run "
                f"`ollama pull {self.model}`."
            )
        wanted = {self.model, f"{self.model}:latest"}
        if not models & wanted:
            return (
                False,
                f"Ollama is running but the model is missing. Run `ollama pull {self.model}`.",
            )
        return True, f"Ollama · {self.model}"

    def generate(self, context: IssueContext) -> Insight:
        try:
            data = _post_json(
                f"{self.base_url}/api/chat",
                {
                    "model": self.model,
                    "stream": False,
                    "format": SCHEMA,
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context.to_prompt()},
                    ],
                },
                timeout=settings.INSIGHTS_TIMEOUT_SECONDS,
            )
        except (urllib.error.URLError, OSError) as exc:
            raise ProviderUnavailable(f"Ollama request failed: {exc}") from exc
        return parse_insight((data.get("message") or {}).get("content", ""))


class GeminiProvider:
    """Google Gemini free tier (hosted demo). Requires GEMINI_API_KEY."""

    name = "gemini"
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Set GEMINI_API_KEY to use the Gemini provider."
        return True, f"Gemini · {self.model}"

    def generate(self, context: IssueContext) -> Insight:
        if not self.api_key:
            raise ProviderUnavailable(self.available()[1])
        try:
            data = _post_json(
                self.endpoint.format(model=self.model),
                {
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": context.to_prompt()}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json",
                        "responseSchema": SCHEMA,
                    },
                },
                timeout=settings.INSIGHTS_TIMEOUT_SECONDS,
                headers={"x-goog-api-key": self.api_key},
            )
        except (urllib.error.URLError, OSError) as exc:
            raise ProviderUnavailable(f"Gemini request failed: {exc}") from exc
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected Gemini response") from exc
        return parse_insight(text)


def get_provider() -> InsightProvider:
    name = settings.INSIGHTS_PROVIDER
    if name == "ollama":
        return OllamaProvider(settings.OLLAMA_URL, settings.INSIGHTS_MODEL or "qwen2.5-coder:3b")
    if name == "gemini":
        return GeminiProvider(
            settings.GEMINI_API_KEY, settings.INSIGHTS_MODEL or "gemini-2.5-flash"
        )
    return DisabledProvider()
