# 0009. Rust ingest edge (phase 3)
- Status: Accepted
- Date: 2026-11-18

## Context
Sentry's Relay, written in Rust, sits in front of the Python stack to absorb load: auth, rate limits, validation and normalization. Ingest is the hottest path in the system.

## Decision
- Phases 1 and 2 keep ingest in Django behind a thin interface.
- Phase 3 adds `relay/`, an axum service that implements the same endpoints and behaviour as [PROTOCOL.md](../PROTOCOL.md). It authenticates keys against Redis (cache-populated by Django), rate-limits, parses envelopes, and produces directly to Kafka `ingest-events`.
- Django ingest stays available as a fallback.

## Consequences
- The ingest tests and fixtures must be runnable against both implementations (black-box HTTP tests).
- A load test compares Django and Rust ingest throughput and latency. That gives a concrete benchmark for the README.
