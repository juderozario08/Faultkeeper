# 0008. Pluggable LLM provider for Issue Insights
- Status: Accepted
- Date: 2026-11-18

## Context
Issue Insights (root-cause summary + suggested fix) needs an LLM. Paid APIs are excluded by [ADR 0007](0007-zero-cost-infrastructure.md). Local models are free but need RAM and ideally a GPU. Containers can't use the GPU on macOS, and Docker on Windows only supports NVIDIA GPUs. Some hosted APIs offer free tiers without a card.

## Decision
- Define `InsightProvider` with `generate(IssueContext) -> Insight`.
- Implementations: `ollama` (default), `gemini` (free tier, hosted demo), `disabled`.
- **Ollama runs natively on the host** (free on macOS and Windows) so it can use the GPU. The backend reaches it at `http://host.docker.internal:11434` (`OLLAMA_URL`). A containerised Ollama is only offered through the `ai` compose profile, for Linux/NVIDIA hosts.
- Default model: a small code-capable model that fits an 8 GB Apple M1. Configurable with `INSIGHTS_MODEL`.
- If the provider is unreachable, Insights shows as unavailable instead of failing.
- Build the context from the exception, frames and context lines, breadcrumbs and tags. Never include user PII, cookies, IPs, request bodies, URL query strings or frame local variables (`vars`).
- Use structured output (Ollama `format` with a JSON schema; Gemini `responseSchema`) for `{summary, root_cause, suggested_fix}`, and validate it against the schema.
- Cache results per issue in `IssueInsight`.

## Consequences
- No vendor lock-in. Adding a provider is one file.
- GPU-accelerated inference on Apple Silicon and Windows, and the default `docker compose up` stays light.
- Quality depends on the model. A larger model can be configured on machines that can handle it.
