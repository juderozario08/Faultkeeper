# 0004. Event bus: Celery on Redis first, Kafka in phase 2
- Status: Accepted
- Date: 2026-11-18

## Context
Ingest must respond fast and never process events inline. Sentry uses Kafka between Relay and its consumers. Kafka is heavier to run and has no reliable free hosted tier without a credit card.

## Decision
- **Phase 1:** ingest enqueues a Celery task (`process_event`) on a Redis broker. Celery beat runs periodic jobs (buffer flush, retention).
- **Phase 2:** an `EVENT_BUS` setting switches ingest to produce to Kafka topic `ingest-events`. A Python consumer runs the same processing code. Processed events go to topic `events` for the ClickHouse writer. Kafka runs in KRaft mode (no ZooKeeper) via the `docker-compose.full.yml` overlay.
- The processing logic is a plain function, `process_event(raw) -> Event`, independent of the transport.

## Consequences
- Both transports share one code path, so swapping is a config change.
- Delivery is at-least-once, so event writes must be idempotent on `(project_id, event_id)`.
- The hosted demo stays on Celery/Redis.
