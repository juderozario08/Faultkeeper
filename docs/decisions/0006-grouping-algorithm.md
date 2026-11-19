# 0006. Fingerprint-based grouping
- Status: Accepted
- Date: 2026-11-18

## Context
Grouping is the core of an error tracker. The same bug must become one issue across thousands of events and across deploys, and different bugs must stay separate.

## Decision
Use the algorithm in [ARCHITECTURE.md §5](../ARCHITECTURE.md#5-grouping-fingerprinting):
- custom `fingerprint` (with `{{ default }}` expansion), else
- exception type(s) + in-app frames' (module|normalized filename, function), else
- type + normalized value, else
- normalized message.

Line and column numbers and raw messages are excluded. The components are joined with newlines and hashed with md5. Rules are versioned via `GROUPING_CONFIG`.

## Consequences
- Stable across deploys that shift line numbers.
- Two different bugs in the same function with the same exception type will merge. Custom fingerprints are the escape hatch, as in Sentry.
- A table-driven test suite covers same-bug and different-bug pairs.
