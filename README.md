# Faultkeeper

**Self-hosted, real-time error monitoring platform — drop-in compatible with the official Sentry SDKs.**

Faultkeeper captures crashes and exceptions from your applications, groups duplicates into issues, streams them to a live dashboard, and helps you understand *why* they happened. Point any official Sentry SDK at a Faultkeeper DSN and it just works — no custom client required.

> Status: **in active development.** See the [roadmap](docs/ROADMAP.md) for what is done and what is next.

---

## Features

| | Feature | Phase |
|---|---|---|
| 🔌 | **Sentry SDK compatible** — accepts the Sentry envelope protocol (`@sentry/browser`, `sentry-sdk` for Python, and more) | 1 |
| 🧬 | **Smart grouping** — stack-trace fingerprinting collapses thousands of identical events into one issue | 1 |
| ⚡ | **Real-time dashboard** — new issues and event counts appear instantly over WebSockets | 1 |
| 🧭 | **Rich context** — stack traces, breadcrumbs, tags, release, environment, browser/OS | 1 |
| 🛡️ | **Per-project rate limiting** and DSN key authentication at the ingest edge | 1 |
| 👥 | **Organizations, projects, and role-based access** (owner / admin / member) | 1 |
| 🌗 | **Light & dark themes**: Tokyo Night dark, Tokyo Night Day light, follows your OS | 1 |
| 💡 | **Issue Insights** — LLM-generated root-cause analysis and suggested fixes, using a local model by default | 1 |
| 🧪 | **Demo apps** — a buggy storefront (`@sentry/browser`) and API (`sentry-sdk` for Python) | 1 |
| 📦 | **Lightweight first-party SDK** (`faultkeeper-js`) written in TypeScript | 2 |
| 🚚 | **Kafka event pipeline** between ingestion and processing | 2 |
| 📈 | **ClickHouse analytics** — fast search and time-series charts over millions of events | 2 |
| 🦀 | **Rust ingest edge** (`relay/`) for high-throughput validation and rate limiting | 3 |
| 🗺️ | **Source map support** — un-minify JavaScript stack traces | 3 |

## Architecture at a glance

```
 Your app + Sentry SDK
         │  POST /api/<project_id>/envelope/
         ▼
 ┌────────────────┐   queue    ┌──────────────────┐        ┌──────────────┐
 │  Ingest edge   │──────────► │  Event pipeline  │──────► │  PostgreSQL  │
 │ auth · limits  │ Redis/Kafka│ normalize · group│        │ issues, meta │
 └────────────────┘            └────────┬─────────┘        └──────┬───────┘
                                        │ (phase 2)               │
                                        ▼                         ▼
                                 ┌─────────────┐          ┌───────────────┐
                                 │ ClickHouse  │ ◄──────► │ Django API +  │ ◄─► Issue Insights
                                 │  analytics  │          │ WebSockets    │     (Ollama / Gemini)
                                 └─────────────┘          └───────┬───────┘
                                                                  ▼
                                                        React + TypeScript dashboard
```

Full details: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Tech stack

| Layer | Technology |
|---|---|
| API & web app | Python 3.12, Django 5, Django REST Framework, Django Channels |
| Background processing | Celery |
| Storage | PostgreSQL 16, Redis 7, ClickHouse *(phase 2)* |
| Event bus | Apache Kafka (KRaft) *(phase 2)* |
| Ingest edge | Rust + axum *(phase 3)* |
| Frontend | React, TypeScript, Vite, TanStack Query, Emotion, ECharts |
| SDK | TypeScript |
| Infrastructure | Docker Compose, GitHub Actions |

## Quick start

> Requires Docker Desktop and Node.js. Works on macOS (Apple Silicon) and Windows. Everything runs locally and costs nothing.

```bash
git clone https://github.com/juderozario08/Faultkeeper.git
cd Faultkeeper
cp .env.example .env
docker compose up --build          # API, workers, Postgres, Redis, demo API

# in two more terminals
cd frontend && npm install && npm run dev
cd demo/buggy-shop && npm install && npm run dev
```

Optional: install [Ollama](https://ollama.com) natively to enable Issue Insights (GPU-accelerated on Apple Silicon and Windows).

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000/api/0/ |
| Demo app ("Buggy Shop") | http://localhost:5174 |

Run the full Sentry-style pipeline (Kafka + ClickHouse):

```bash
docker compose --profile full up --build
```

## Sending your first error

Create a project in the dashboard, copy its DSN, and use the **official Sentry SDK**:

```js
import * as Sentry from "@sentry/browser";

Sentry.init({ dsn: "http://<public_key>@localhost:8000/<project_id>" });

throw new Error("Hello, Faultkeeper!");
```

```python
import sentry_sdk

sentry_sdk.init(dsn="http://<public_key>@localhost:8000/<project_id>")
1 / 0
```

The error appears on the dashboard in real time.

## Project layout

```
backend/            Django project (ingest, processing, issues API, realtime, insights)
frontend/           React + TypeScript dashboard
sdk/faultkeeper-js/ First-party TypeScript SDK
demo/buggy-shop/    Demo storefront with intentional bugs
demo/buggy-shop-api/ Demo Python API with intentional bugs
relay/              Rust ingest edge (phase 3)
loadtest/           Load-testing scripts and benchmark results
docs/               Architecture, protocol, decisions, roadmap
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — components, data flow, data model, API
- [Ingest protocol](docs/PROTOCOL.md) — the subset of the Sentry envelope protocol Faultkeeper accepts
- [Architecture Decision Records](docs/decisions/) — why things are the way they are
- [Roadmap](docs/ROADMAP.md) — phases and progress
- [Glossary](docs/GLOSSARY.md) — events, issues, fingerprints, envelopes, DSNs…
- [Contributing](CONTRIBUTING.md) — conventions, workflow, testing

## Benchmarks

*Coming soon* — ingest throughput, p99 latency, and grouping accuracy measured with the scripts in `loadtest/`.

## Acknowledgements

Faultkeeper is an independent project and is not affiliated with or endorsed by Functional Software, Inc. (Sentry). It implements the publicly documented [Sentry SDK protocol](https://develop.sentry.dev/sdk/) so that the MIT-licensed official SDKs can report to it; no Sentry server code is used.
