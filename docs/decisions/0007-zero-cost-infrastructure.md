# 0007. Zero-cost infrastructure
- Status: Accepted
- Date: 2026-11-18

## Context
The project must cost nothing to develop, run, demo or host, and must not require a credit card anywhere.

## Decision
- **Primary environment:** local Docker Compose with everything included. Demos run locally.
- **Hosted demo (phase 1 features only):** Render free web service (Django + worker in one container), Neon free Postgres, Upstash free Redis, Cloudflare Pages for static frontends, Gemini free tier for Insights.
- Kafka, ClickHouse and the Rust edge run locally only.
- Verify every provider's free-tier terms at deploy time, and reject any that require a card.
- Keep resource usage small: 30-day retention, ingest size limits, rate limits.

## Consequences
- The hosted demo may cold-start slowly (free services sleep when idle). Live presentations use the local stack.
- The hosted Celery setup must respect Redis request quotas. If quotas are too tight, use a low-polling broker configuration or eager mode for the demo only.
