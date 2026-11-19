# 0008. Pluggable LLM provider for Issue Insights
- Status: Accepted
- Date: 2026-11-18

## Context
Issue Insights (root-cause summary + suggested fix) needs an LLM. Paid APIs are excluded by [ADR 0007](0007-zero-cost-infrastructure.md). Local models are free but need RAM. Some hosted APIs offer free tiers without a card.

## Decision
- Define `InsightProvider` with `generate(IssueContext) -> Insight`.
- Implementations: `ollama` (default, local, via the `ollama` container), `gemini` (free tier, hosted demo), `disabled`.
- Select it with `INSIGHTS_PROVIDER` / `INSIGHTS_MODEL`.
- Build the context from the exception, frames and context lines, breadcrumbs and tags. User PII, cookies, IPs and request bodies are never included.
- Require JSON output `{summary, root_cause, suggested_fix}`, with one retry on invalid output.
- Cache results per issue in `IssueInsight`.

## Consequences
- No vendor lock-in. Adding a provider is one file.
- Quality depends on the model. The default is a small code-capable model that runs on a typical laptop.
