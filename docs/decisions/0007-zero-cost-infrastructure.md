# 0007. Zero-cost infrastructure
- Status: Accepted
- Date: 2026-11-18

## Context
The project must cost nothing to develop, run, demo or host, and must not require a credit card anywhere. It must run on both macOS (Apple Silicon) and Windows.

## Decision
- **Primary environment:** local Docker Compose (profiles: default core, `full`, `ai`), with the two Vite apps and Ollama running natively. Demos run locally. All images must publish `linux/arm64` builds.
- **Hosted demo (phase 1 features only):**
  - Render free web service runs Django **and serves the built dashboard** (WhiteNoise), so the session cookie is same-origin. Cross-site cookies are blocked by Safari and Firefox.
  - Neon free tier for Postgres.
  - Cloudflare Pages for the static Buggy Shop (ingest uses CORS `*`, no cookies). It's built unminified until phase 3 source maps.
  - Gemini free tier for Insights.
  - **Single-process mode** (`DEPLOY_MODE=single`): in-process worker thread, in-memory channel layer, in-memory cache. No Redis, which avoids free-tier request quotas and fits in 512 MB.
- Kafka, ClickHouse and the Rust edge run locally only.
- Verify every provider's free-tier terms at deploy time, and reject any that require a card.
- Keep resource usage small: 30-day retention, ingest size limits, rate limits.

## Consequences
- The hosted demo may cold-start slowly (free services sleep when idle). Live presentations use the local stack.
- Single-process mode can't scale horizontally. That's acceptable for a demo, and the standard mode is unchanged.
