# 0005. Storage: Postgres for metadata + payloads, ClickHouse for analytics
- Status: Accepted
- Date: 2026-11-18

## Context
Sentry stores metadata (orgs, projects, issues) in Postgres, full event payloads in "nodestore", and searchable/aggregatable event rows in ClickHouse via Snuba.

## Decision
- **Postgres 16:** all relational metadata, plus an `Event` table holding the full payload as JSONB, which serves as our nodestore.
- **ClickHouse (phase 2):** a flattened `events` table (ReplacingMergeTree, partitioned by day, 30-day TTL) for time-series stats and search. It's accessed through a thin internal module, `snuba_lite`, instead of a separate service.
- Before phase 2, stats queries run against Postgres. After it, the `stats` endpoint reads from ClickHouse.
- Events are kept for 30 days by default. Issues are kept indefinitely.

## Consequences
- Phase 1 works with Postgres alone.
- The ClickHouse writer batches inserts (by size or every second) because ClickHouse handles large batches much better than single-row inserts.
