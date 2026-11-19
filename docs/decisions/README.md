# Architecture Decision Records

Each file records one significant decision: the context, the decision, and its consequences. ADRs are **append-only**. To change a decision, add a new ADR that supersedes the old one and update the old one's status line.

| # | Decision | Status |
|---|---|---|
| [0001](0001-mirror-sentry-architecture.md) | Mirror Sentry's production architecture | Accepted |
| [0002](0002-sentry-sdk-protocol-compatibility.md) | Be compatible with the official Sentry SDKs | Accepted |
| [0003](0003-django-monolith.md) | Django + DRF + Channels monolith for API, ingest, and realtime | Accepted |
| [0004](0004-event-bus-celery-then-kafka.md) | Celery on Redis first, Kafka in phase 2 | Accepted |
| [0005](0005-storage-postgres-and-clickhouse.md) | Postgres for metadata + payloads, ClickHouse for analytics | Accepted |
| [0006](0006-grouping-algorithm.md) | Fingerprint-based grouping | Accepted |
| [0007](0007-zero-cost-infrastructure.md) | Zero-cost infrastructure | Accepted |
| [0008](0008-pluggable-llm-provider.md) | Pluggable LLM provider for Issue Insights | Accepted |
| [0009](0009-rust-ingest-edge.md) | Rust ingest edge in phase 3 | Accepted |
| [0010](0010-frontend-stack.md) | Frontend stack | Accepted |
| [0011](0011-realtime-websockets.md) | Push updates over WebSockets | Accepted |
| [0012](0012-theming-tokyo-night.md) | Light + dark themes; dark = Tokyo Night, light = Tokyo Night Day | Accepted |

## Template

```markdown
# NNNN. Title
- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
## Decision
## Consequences
```
