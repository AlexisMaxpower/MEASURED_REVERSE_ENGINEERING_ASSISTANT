# Build / Reuse Check — Pass 13 Snapshot Guard

## Decision

**BUILD a thin local guard around the existing SQLite connection; REUSE all persistence and query semantics.**

No external dependency, database service, cache, ORM or concurrency framework is added.

## Reused components

- existing `SQLiteLifecycleReadOnlySession` lifecycle;
- authoritative `lifecycle_store.version`;
- existing `lifecycle_read_model_meta.snapshot_version` publication boundary;
- existing migration metadata;
- normalized lifecycle repository;
- materialized/keyset engineering knowledge repositories;
- existing `LifecycleReadOnlyStaleError` and `refresh()` contract.

## Alternatives rejected

### Long-lived SQLite read transaction

Rejected because a reader kept open across application calls can hold a rollback-journal read lock and block writer commit. The project does not currently mandate WAL mode.

### WAL as a Pass-13 prerequisite

Rejected because changing journal mode is a broader persistence/deployment decision and is unnecessary for the invariant being fixed.

### Copy/snapshot database per reader

Rejected as duplicate storage/backup machinery with higher I/O and lifecycle complexity.

### Independent generation cache

Rejected because it would create a second consistency authority. Existing durable metadata is already the correct source of truth.

## Chosen trade-off

Each repository statement performs small metadata checks before execution and after row fetch. This adds bounded local SQLite reads but preserves writer availability and fail-closed correctness without changing storage semantics.

## Shared ownership impact

None. Changes are contained under Chat 5.

## Verification criterion

An open read-only session must allow a separate writer to commit, reject all later repository reads under the old generation, and resume only after explicit refresh.

Evidence:

```text
implementation SHA: a26c1d8f6927e3ebdfcf69d7f759893cd7b139bd
MREA CI: 36806176020 — SUCCESS
Chat 5: 73 passed in 3.05s
```
