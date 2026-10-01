# Build / Reuse Check — Pass 12 Materialized Knowledge

## Decision

**BUILD a thin derived projection; REUSE all existing lifecycle/query semantics.**

No external database, cache, ORM, task queue, analytics engine, or new runtime dependency is introduced.

## Reused components

Pass 12 deliberately reuses:

- authoritative `SQLiteLifecycleStore` snapshot transaction;
- `SQLiteLifecycleReadModelWriter` normalized projection;
- `lifecycle_read_model_meta.snapshot_version` as the existing publication boundary;
- `SQLiteKeysetEngineeringKnowledgeRepository` cursor validation and inherited methods;
- Pass-11 failure-pattern ordering/keyset definition;
- Pass-10 HMAC cursor wrapper without modification;
- existing `RevisionOutcomeSummary` and `FailurePatternSummary` public result models.

## Why not a separate cache service

A Redis/materialized-service layer would introduce a second commit/invalidating authority and a distributed consistency problem that the current product does not need.

The SQLite lifecycle store already has an atomic projection commit boundary. Using that boundary keeps:

```text
snapshot write
normalized projection
materialized aggregates
```

inside one durable transaction.

## Why not recompute on first read

Lazy in-process caching would make cache generation dependent on process lifetime and would require independent invalidation/locking. It would also not help a new read-only process before its first expensive query.

Persisted materialized rows are deterministic, restart-safe and backup-compatible because they are part of the same database generation.

## Why a schema migration/trigger

The refresh trigger attaches derived-data rebuild to the existing `snapshot_version` publication statement without duplicating the lifecycle writer or adding a second application-level commit path.

Migration v4 invalidates the old read-model version once. Existing store repair logic then backfills both normalized and materialized projections from the authoritative snapshot.

## Compatibility choice

Legacy v1 cursors are not remapped to the materialized execution path. They explicitly reuse the old raw OFFSET implementation.

Reason: an offset cursor encodes position in the historical query contract; silently changing the execution surface during an in-flight traversal creates avoidable compatibility risk. New traversals use v2 keyset state on materialized rows.

## Shared ownership impact

None.

No change is required in:

- `core/contracts/**`;
- Chat 1–4 code;
- root integration tests;
- `.github/workflows/**`;
- central orchestration documents.

## Verification criterion

The implementation is accepted locally only if materialized direct results are equal to the raw aggregate repository and all existing Chat-5/canonical/CAD→Lifecycle gates remain green.

Evidence:

```text
implementation SHA: 0e4b2df0b144fe7116b7e94141be85266a0820fc
MREA CI: 36802306777 — SUCCESS
Chat 5: 72 passed in 11.64s
```
