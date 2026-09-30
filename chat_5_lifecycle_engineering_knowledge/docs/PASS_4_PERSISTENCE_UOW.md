# Pass 4 — Durable Lifecycle Persistence & Unit of Work

## Authorization and base

Pass 4 was started by direct user instruction after Chat 5 Pass 3 was frozen.

At start time GitHub `main` still pointed to the Pass-3 directive baseline and did not yet contain an orchestrator-issued `OD-004`. Therefore this worker branch deliberately starts from the exact frozen Chat 5 Pass 3 handoff commit:

```text
cdc5baceb281b657680d1e38cc49ea8094669ad8
```

No Chat-6-owned file or shared contract was modified.

## Goal

Close the persistence/atomicity gap left explicit in Pass 3:

```text
canonical lifecycle mutation
+ physical-instance mutation
→ one application transaction
→ one durable SQLite snapshot commit
```

The pass is intentionally a persistence foundation, not a final query-optimized relational schema.

## Repository boundary

Added `LifecycleRepository` as the internal Chat 5 persistence port.

The existing in-memory domain store remains valid and now exposes the same transactional boundary. `SQLiteLifecycleStore` implements the same lifecycle aggregate surface while adding durable commits.

No shared MREA contract was changed.

## LifecycleUnitOfWork

`LifecycleUnitOfWork` is the application transaction boundary.

It groups the existing services:

- RevisionService;
- CADRevisionPreparationService;
- ManufacturingService;
- InstallationService;
- TestService;
- FailureService;
- PhysicalPartLifecycleService.

Usage:

```python
store = SQLiteLifecycleStore("lifecycle.db")
uow = LifecycleUnitOfWork(store)

with uow.transaction():
    uow.revisions.create(...)
    uow.manufacturing.record(...)
    uow.physical.register_manufactured(...)
```

The outer Unit of Work owns persistence commit/rollback. Existing service semantics are reused rather than duplicated.

## Atomic rollback

`InMemoryLifecycleStore.transaction()` now supports:

- outer transaction snapshots;
- nested transaction depth;
- rollback of all lifecycle collections and sequence counters;
- rollback-only behavior when a nested transaction fails;
- durable-store begin/commit/rollback hooks.

This closes the specific Pass 3 risk where a canonical event could be recorded before a later physical-instance write failed.

For a Unit of Work, any exception restores:

- revisions;
- manufacturing records;
- installations;
- tests;
- failures;
- canonical events;
- physical instances;
- physical events;
- both event sequence counters.

## SQLite persistence

`SQLiteLifecycleStore` uses Python stdlib `sqlite3`; no new third-party dependency is introduced.

The current durable representation is one versioned lifecycle aggregate snapshot:

```text
lifecycle_store
- singleton
- schema_version
- version
- payload
```

Snapshot schema:

```text
mrea.lifecycle-snapshot.v1
```

The payload preserves the complete current Chat 5 aggregate, including:

- CAD revision linkage and artifact metadata;
- Decimal manufacturing cost;
- canonical lifecycle events;
- physical instance identities;
- physical lifecycle events;
- explicit physical test outcomes;
- removal/replacement references.

The snapshot is serialized deterministically with sorted JSON keys.

## Concurrency guard

Each durable store instance tracks the SQLite `version` it loaded.

Before an outer writer transaction:

```text
BEGIN IMMEDIATE
→ read current version
→ compare with loaded_version
```

If another writer already committed a newer state, the stale writer is rejected with `LifecycleConcurrencyError`.

It must explicitly `reload()` before attempting another write.

This prevents a stale in-memory aggregate from silently overwriting a newer durable lifecycle state.

## Fail-closed transaction requirement

A mutating legacy service call against `SQLiteLifecycleStore` outside `LifecycleUnitOfWork.transaction()` is rejected with `LifecycleTransactionRequiredError`.

Because legacy services historically mutate an in-memory mapping before appending an event, the durable store reloads its last committed snapshot before raising the error. This discards the unsafe staged mutation and keeps memory aligned with durable state.

## Build / Reuse decision

Reused:

- Python stdlib `sqlite3`;
- all Pass 1-3 domain models;
- existing services;
- existing physical state machine;
- existing canonical lifecycle adapter.

Not introduced:

- ORM;
- migration framework;
- external database driver;
- duplicate lifecycle service layer;
- shared contract changes.

## Verification

New tests cover:

1. durable SQLite round-trip of VERIFIED CAD revision, manufacturing Decimal metadata, physical instance, installation, test and ACTIVE state;
2. canonical LifecycleEvent v1 remains thin after reload;
3. forced failure after canonical installation write but before physical append rolls the entire Unit of Work back;
4. failed transaction does not increment durable version;
5. stale concurrent writer is rejected;
6. `reload()` permits a writer to continue from the latest durable version;
7. SQLite mutation outside Unit of Work fails closed and does not survive reopen;
8. in-memory transaction restores its pre-transaction state on exception.

Independent GitHub-hosted Chat 5 CI on implementation SHA `5a529bfbe4f51e0632d0d5d76b342a66d38d299d`:

```text
20 passed in 0.17s
```

Canonical contract job also passed on the same workflow run.

## Limitations

This pass does not claim a final production database design.

Still open:

- normalized/query-optimized relational schema;
- explicit schema migration framework;
- repository-native query methods instead of aggregate snapshot loading;
- multi-process read refresh policy;
- REST/API;
- database backup/restore policy;
- field-device integration;
- AI/semantic failure analysis.

The current snapshot approach is deliberately chosen to establish correctness, atomicity, durability and stale-writer protection before optimizing persistence shape.
