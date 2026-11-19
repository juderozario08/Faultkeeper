# Contributing to Faultkeeper

## Before you change anything
1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the relevant [ADRs](docs/decisions/).
2. If your change contradicts an ADR, write a new ADR that supersedes it **in the same PR**.
3. If your change alters behaviour described in `ARCHITECTURE.md` or `PROTOCOL.md`, update those docs in the same PR.
4. Tick off the matching item in [docs/ROADMAP.md](docs/ROADMAP.md) when it is done.

## Workflow
- Branch from `main`: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, `chore/<short-name>`.
- Small, focused commits. Each one should leave the tree green (`./scripts/check.sh --quick`).
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  ```
  feat(ingest): parse envelopes without item length
  fix(grouping): ignore cache-busting hashes in filenames
  docs(adr): add 0012 alert rules
  ```
  Scopes: `ingest`, `processing`, `grouping`, `issues`, `orgs`, `realtime`, `insights`, `snuba`, `relay`, `frontend`, `sdk`, `demo`, `loadtest`, `infra`, `ci`, `docs`, `adr`.

## Code conventions

### Python (`backend/`)
- Python 3.12, Django 5, DRF. Dependencies via `uv`.
- `ruff check` + `ruff format`, `mypy` (strict on `ingest`, `processing`).
- Business logic lives in plain functions or services (`services.py`), not in views or serializers. Views stay thin.
- Never process events in the request path; ingest only authenticates, limits, parses, and enqueues.
- Writes must be idempotent where messages can be redelivered (`(project_id, event_id)` unique).
- Use Sentry's vocabulary (see [GLOSSARY](docs/GLOSSARY.md)): `Group` for issues, `times_seen`, `culprit`, `fingerprint`, etc.
- Tests: `pytest` + `pytest-django`, colocated in `<app>/tests/`. Table-driven where possible.

### TypeScript (`frontend/`, `sdk/`, `demo/`)
- Strict TypeScript, no `any` without a comment explaining why.
- Server state through TanStack Query; no ad-hoc fetching in components.
- Styling with Emotion; shared primitives in `frontend/src/components`.
- `oxlint`, `tsc -b`, `vitest`.

### Rust (`relay/`)
- `cargo fmt`, `cargo clippy -- -D warnings`, `cargo test`.

## Running checks locally
Everything CI runs, in one command: `./scripts/check.sh` (`scripts\check.cmd` on Windows). Use `--quick` to skip the Docker steps. Individual commands:
```bash
# backend
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
# frontend
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Security and privacy
- Never commit secrets. `.env` is git-ignored; add new variables to `.env.example` with safe defaults.
- PII (user emails, IPs, cookies, auth headers) must be scrubbed before storage where specified and **must never** be sent to an LLM provider.
- Do not copy code from the Sentry server repository (FSL-licensed). Implement from the public protocol docs only. Official SDKs (MIT) may be used as dependencies.
