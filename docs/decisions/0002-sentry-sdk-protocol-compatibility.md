# 0002. Be compatible with the official Sentry SDKs
- Status: Accepted
- Date: 2026-11-18

## Context
A custom-only SDK would limit adoption and prove little. The Sentry SDKs are MIT-licensed, and the wire protocol (DSN, envelopes, event schema) is publicly documented at develop.sentry.dev. The Sentry *server* is under the Functional Source License (FSL).

## Decision
- Implement the envelope (`/api/<id>/envelope/`) and legacy store (`/api/<id>/store/`) endpoints from the public protocol docs. Official SDKs work by changing only the DSN.
- **Never copy or adapt Sentry server source code.** Use only the public docs and observed SDK traffic.
- Later (after phase 1), ship a small first-party SDK (`faultkeeper-js`) to understand and own the client side. Phase 1 demos use the official SDKs only.
- Demo with **both** official SDKs: `@sentry/browser` (Buggy Shop) and `sentry-sdk` for Python (Buggy Shop API).
- Acknowledge unsupported item types with 2xx and drop them.

## Consequences
- Captured real-SDK envelopes become test fixtures, so compatibility is tested continuously.
- The supported subset is documented in [PROTOCOL.md](../PROTOCOL.md).
- The README states that the project is not affiliated with Sentry.
