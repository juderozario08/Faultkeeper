# 0001. Mirror Sentry's production architecture
- Status: Accepted
- Date: 2026-11-18

## Context
Faultkeeper is a learning-focused, portfolio-grade error tracker. Its value comes from showing real-world, at-scale design, not from being the simplest thing that works. Sentry is the reference product in this space, and much of its architecture is public: the Django monolith, Relay in Rust, Kafka, ClickHouse via Snuba, Symbolicator, and Postgres + Redis.

## Decision
Copy the *shape* of Sentry's architecture, with each component scaled down:
SDK → ingest edge (Relay) → event bus (Kafka) → processing workers → Postgres (metadata + nodestore) and ClickHouse (analytics) → Django API → React/TypeScript UI.

Deliver it in phases so a working product exists at every step:
- **Phase 1:** Django, Celery, Postgres, Redis, Channels, React
- **Phase 2:** Kafka, ClickHouse
- **Phase 3:** Rust edge, source maps

## Consequences
- More moving parts than a toy app. Docker Compose profiles keep the default `docker compose up` light.
- Every component has a clear Sentry counterpart, which makes the design easy to explain and justify.
- Deliberate simplifications (no separate Snuba service, no Memcached, one worker type) are listed in ARCHITECTURE.md.
