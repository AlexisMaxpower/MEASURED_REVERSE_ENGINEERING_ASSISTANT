# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-29**
- Branch: `chat-5/pass-4`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 4 authorization: **direct user instruction; no OD-004 present in GitHub at branch start**
- Base SHA: `cdc5baceb281b657680d1e38cc49ea8094669ad8` (frozen Chat 5 Pass 3)
- State: **durable persistence + Unit of Work implemented; final handoff pending downstream gate**

## Preserved baseline

Still active:

- Revision / Manufacturing / Installation / Test / Failure domain;
- CAD-linked Revision preparation;
- CAD verification manufacturing eligibility gate;
- canonical `LifecycleEvent v1` adapter;
- physical part identity/state machine;
- equipment/position occupancy protection;
- exact failure evidence linkage;
- removal/replacement/supersession semantics.

No shared MREA contract or canonical fixture was changed.

## Pass 4 additions

### Repository port

Added internal `LifecycleRepository` protocol for the lifecycle aggregate.

It exposes the existing revision/manufacturing/test/failure/canonical-event and physical-instance/event collections plus a transaction boundary.

### Unit of Work

Added `LifecycleUnitOfWork`.

It reuses existing services and provides one outer transaction spanning:

- revision creation;
- CAD revision preparation;
- manufacturing;
- installation;
- test;
- failure;
- physical instance transitions.

This allows canonical and physical writes to succeed or roll back together.

### In-memory transaction semantics

`InMemoryLifecycleStore` now has:

- nested transaction depth;
- outer state snapshot;
- rollback of all collections;
- rollback of canonical and physical sequence counters;
- rollback-only behavior after nested failure;
- overridable begin/commit/rollback hooks for durable repositories.

Existing non-transactional in-memory callers remain backward compatible.

### SQLite durable store

Added `SQLiteLifecycleStore` using only Python stdlib `sqlite3`.

Durable snapshot schema:

```text
mrea.lifecycle-snapshot.v1
```

SQLite table:

```text
lifecycle_store(
    singleton,
    schema_version,
    version,
    payload
)
```

The complete current lifecycle aggregate is committed as one deterministic JSON snapshot so revision-level canonical history and physical-instance history share one atomic persistence boundary.

Persisted data includes:

- Revision and CAD linkage;
- CAD artifact metadata;
- ManufacturingRecord including Decimal cost;
- Installation/Test/Failure records;
- canonical LifecycleEvent sequence;
- PhysicalPartInstance;
- physical lifecycle events and test outcomes;
- replacement identity.

### Optimistic concurrency

Each SQLite repository tracks `loaded_version`.

Writer begin sequence:

```text
BEGIN IMMEDIATE
→ read DB version
→ require DB version == loaded_version
```

A stale writer receives `LifecycleConcurrencyError` and must `reload()` before continuing.

This prevents silent overwrite of a newer lifecycle snapshot.

### Transaction-required durable writes

SQLite mutation outside `LifecycleUnitOfWork.transaction()` raises `LifecycleTransactionRequiredError`.

If a legacy service already staged an in-memory mapping mutation before event append, the durable store reloads the last committed state before raising. Therefore the unsafe mutation does not remain visible or survive reopen.

## Independent verification

GitHub workflow run on implementation SHA `5a529bfbe4f51e0632d0d5d76b342a66d38d299d`:

### Chat 5 / Lifecycle

```text
20 passed in 0.17s
```

Status: **SUCCESS**.

### Contracts / canonical fixtures

Status: **SUCCESS**.

### Chat 4 generic prerequisite

Status: **SUCCESS**.

### Integration / Chat 4 -> Chat 5

Final handoff waits for this downstream job to complete on the Pass-4 implementation/documentation head.

## New tests

`tests/test_persistence_uow.py` adds deterministic coverage for:

1. VERIFIED CAD revision durable round-trip;
2. CAD artifact metadata retention;
3. Decimal manufacturing cost retention;
4. physical instance/install/test/ACTIVE durable round-trip;
5. unchanged canonical LifecycleEvent v1 after reload;
6. forced failure between canonical and physical writes rolls both back;
7. failed transaction does not advance durable version;
8. stale writer rejection;
9. reload then successful continuation;
10. direct SQLite mutation outside Unit of Work rejected and discarded;
11. in-memory transaction rollback.

## Files added in Pass 4

- `src/mrea_lifecycle/repository.py`;
- `src/mrea_lifecycle/unit_of_work.py`;
- `src/mrea_lifecycle/persistence.py`;
- `tests/test_persistence_uow.py`;
- `docs/PASS_4_PERSISTENCE_UOW.md`.

## Files modified in Pass 4

- `src/mrea_lifecycle/store.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Build / Reuse

No third-party dependency was introduced.

Reused:

- Python `sqlite3`;
- all existing Chat 5 domain models;
- existing lifecycle services;
- physical state machine;
- canonical lifecycle adapter.

## Known limitations

Not implemented yet:

- normalized/query-optimized relational model;
- explicit migration framework;
- repository-native query API;
- automatic long-lived reader refresh;
- REST/API;
- database backup/restore tooling;
- field-device synchronization;
- AI / semantic engineering knowledge analysis.

`LifecycleUnitOfWork` currently adapts the pre-existing services structurally while their constructor type annotations still name `InMemoryLifecycleStore`. Runtime behavior is repository-compatible; a future cleanup can migrate those annotations to the protocol without changing behavior.

## Handoff rule

After `ORCHESTRATOR_HANDOFF.md` is updated, `chat-5/pass-4` is frozen. No later commit is allowed unless Chat 6 explicitly requests a correction.
