"""Builds the privacy-safe context sent to an LLM (ARCHITECTURE.md §7).

Never included: user data, IPs, cookies, request headers/bodies, URL query strings,
and frame local variables (`vars`).
"""

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from issues.models import Group

MAX_FRAMES = 8
MAX_BREADCRUMBS = 15
SAFE_TAG_KEYS = {"browser", "os", "runtime", "release", "environment", "level", "url", "handled"}
_URL = re.compile(r"https?://[^\s'\"<>]+")


def strip_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def scrub_text(text: str, limit: int = 300) -> str:
    text = _URL.sub(lambda m: strip_query(m.group(0)), text)
    return text[:limit]


@dataclass
class IssueContext:
    title: str
    culprit: str
    platform: str
    level: str
    times_seen: int
    release: str | None
    environment: str | None
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    message: str | None = None
    breadcrumbs: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def to_prompt(self) -> str:
        lines = [
            f"Issue: {self.title}",
            f"Culprit: {self.culprit or 'unknown'}",
            f"Platform: {self.platform} · Level: {self.level} · Occurrences: {self.times_seen}",
        ]
        if self.release or self.environment:
            lines.append(f"Release: {self.release or '-'} · Environment: {self.environment or '-'}")
        if self.message:
            lines.append(f"Message: {self.message}")
        for i, exc in enumerate(self.exceptions):
            label = "Exception" if i == len(self.exceptions) - 1 else "Caused by"
            lines.append(f"\n{label}: {exc['type']}: {exc['value']}")
            lines.append("Stack (most recent call last):")
            for frame in exc["frames"]:
                lines.append(
                    f"  {frame['location']} in {frame['function']} (line {frame['lineno']})"
                )
                for code in frame["code"]:
                    lines.append(f"      {code}")
        if self.breadcrumbs:
            lines.append("\nBreadcrumbs (oldest first):")
            lines.extend(f"  - {crumb}" for crumb in self.breadcrumbs)
        if self.tags:
            lines.append("\nTags: " + ", ".join(f"{k}={v}" for k, v in sorted(self.tags.items())))
        return "\n".join(lines)


def _frame(frame: dict[str, Any]) -> dict[str, Any]:
    code: list[str] = []
    pre = frame.get("pre_context") or []
    if frame.get("context_line") is not None:
        code = [
            *pre[-3:],
            f"{frame['context_line']}    <-- here",
            *(frame.get("post_context") or [])[:2],
        ]
    location = frame.get("module") or strip_query(
        str(frame.get("filename") or frame.get("abs_path") or "?")
    )
    return {
        "location": location,
        "function": frame.get("function") or "?",
        "lineno": frame.get("lineno", "?"),
        "code": [str(c)[:200] for c in code],
    }


def build_context(group: Group, payload: dict[str, Any]) -> IssueContext:
    exceptions = []
    for exc in (payload.get("exception") or {}).get("values") or []:
        frames = (exc.get("stacktrace") or {}).get("frames") or []
        in_app = [f for f in frames if f.get("in_app")] or frames
        exceptions.append(
            {
                "type": exc.get("type") or "Error",
                "value": scrub_text(str(exc.get("value") or "")),
                "frames": [_frame(f) for f in in_app[-MAX_FRAMES:]],
            }
        )

    crumbs = []
    for crumb in ((payload.get("breadcrumbs") or {}).get("values") or [])[-MAX_BREADCRUMBS:]:
        data = crumb.get("data") or {}
        text = crumb.get("message") or ""
        if not text and isinstance(data, dict) and data.get("url"):
            url = strip_query(str(data["url"]))
            text = f"{data.get('method', '')} {url} -> {data.get('status_code', '?')}"
        crumbs.append(
            f"[{crumb.get('category') or crumb.get('type') or 'default'}] {scrub_text(str(text))}"
        )

    tags = {
        str(k): scrub_text(str(v), 100)
        for k, v in payload.get("tags") or []
        if str(k) in SAFE_TAG_KEYS
    }
    logentry = payload.get("logentry") or {}
    return IssueContext(
        title=group.title,
        culprit=group.culprit,
        platform=group.platform,
        level=group.level,
        times_seen=group.times_seen,
        release=payload.get("release"),
        environment=payload.get("environment"),
        exceptions=exceptions,
        message=scrub_text(str(logentry.get("formatted"))) if logentry.get("formatted") else None,
        breadcrumbs=crumbs,
        tags=tags,
    )
