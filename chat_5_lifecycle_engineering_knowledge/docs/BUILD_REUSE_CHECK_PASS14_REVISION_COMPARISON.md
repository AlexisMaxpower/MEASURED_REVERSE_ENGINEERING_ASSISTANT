# Build / Reuse Check — Pass 14 Durable Revision Comparison

## Decision

**REUSE existing semantics and durable infrastructure; build only the missing durable adapter.**

## Reused assets

Pass 14 reuses:

- `RevisionComparisonResult` from the original projection layer;
- historical revision-level `LifecycleStateProjection` semantics;
- normalized SQLite read model tables;
- `SQLiteMaterializedEngineeringKnowledgeRepository` as the current durable knowledge base class;
- Pass-13 snapshot-guarded read-only connection/session;
- existing GET-only HTTP adapter and JSON serialization;
- existing `400 invalid_request` HTTP error boundary.

## Why no new database structure

All required facts already exist transactionally in the normalized committed read model:

```text
lifecycle_revisions
lifecycle_manufacturing
lifecycle_tests
lifecycle_failures
lifecycle_events_relational
```

Adding another table/materialized view would duplicate state without a demonstrated performance requirement. Pass 14 therefore uses direct snapshot-guarded reads and leaves `SQLITE_RELATIONAL_SCHEMA_VERSION = 4` unchanged.

## Why not reuse the in-memory object directly

The original `RevisionComparison` depends on `InMemoryLifecycleStore` and in-memory repository methods. Rehydrating or reconstructing that store merely to compare two durable revisions would:

- duplicate committed state in memory;
- introduce another consistency boundary;
- bypass the SQL-native read model;
- weaken Pass-13 snapshot guarantees.

The durable repository instead reuses the *result type and semantics*, while sourcing facts directly from the authoritative committed projection.

## Why no new shared contract

Revision comparison is an internal engineering-knowledge query, not a new cross-chat lifecycle event or CAD transfer fact. Existing shared contracts do not need modification.

## Why HTTP v1 remains valid

The new endpoint is additive and returns data through the existing envelope/serialization rules. No existing route, required field, cursor or error contract changes. Therefore no HTTP schema version bump is required.

## Explicit non-goals

No external dependency, AI model, ranking algorithm, statistical model, recommendation engine or causal inference library was introduced.

## Verification

Implementation + transport:

```text
SHA 8f5394c9ad2ffe1bfefc02021b78a9c7a17320d0
MREA CI 36811581113 — SUCCESS
```

The required Chat-5, shared-contract and Chat-4→Chat-5 gates passed.
