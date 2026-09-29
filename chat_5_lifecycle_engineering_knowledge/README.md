# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 4 durable persistence foundation implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 4: **direct user instruction; OD-004 отсутствовал в GitHub на момент старта**  
Рабочая ветка: `chat-5/pass-4`  
База ветки: `cdc5baceb281b657680d1e38cc49ea8094669ad8` (frozen Pass 3 handoff)

## Назначение области

Chat 5 ведёт инженерную историю ревизии и фактическую жизнь конкретного изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed
→ Tested
→ Active / In service
→ Failed
→ Removed
→ Superseded by replacement
```

## Реализовано

### Pass 1

- Revision / Manufacturing / Installation / Test / Failure domain;
- deterministic lifecycle queries/projections;
- canonical `LifecycleEvent v1` adapter.

### Pass 2

- canonical CADPackage + CADVerificationReport → lifecycle Revision;
- CAD traceability retention;
- only VERIFIED CAD revisions may manufacture.

### Pass 3

- `PhysicalPartInstance`;
- physical state machine;
- exact instance linkage on installation/test/failure;
- PASSED test gate before ACTIVE;
- removal/replacement/supersession;
- equipment/position occupancy protection.

### Pass 4

Добавлен durable persistence/application boundary:

- `LifecycleRepository` persistence port;
- nested atomic transactions in `InMemoryLifecycleStore`;
- `LifecycleUnitOfWork` across revision/manufacturing/installation/test/failure/physical services;
- `SQLiteLifecycleStore` using stdlib `sqlite3`;
- versioned durable snapshot `mrea.lifecycle-snapshot.v1`;
- atomic canonical + physical commit/rollback;
- optimistic stale-writer protection through `loaded_version`;
- explicit `reload()` after concurrent writer advancement;
- fail-closed rejection of SQLite mutations outside Unit of Work;
- deterministic round-trip of CAD links, Decimal cost, canonical events and physical events.

## Transaction model

Recommended durable write path:

```python
store = SQLiteLifecycleStore("lifecycle.db")
uow = LifecycleUnitOfWork(store)

with uow.transaction():
    uow.revisions.create(...)
    uow.manufacturing.record(...)
    uow.physical.register_manufactured(...)
```

Any exception rolls the whole Unit of Work back, including both canonical and physical event streams.

A stale SQLite writer is rejected instead of overwriting a newer committed lifecycle state.

## Shared-contract boundary

No shared MREA contract was changed.

Canonical `mrea.lifecycle-event.v1` still exports only:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

Physical states and persistence metadata remain internal to Chat 5.

## Verification

Independent GitHub-hosted Chat 5 CI on Pass-4 implementation:

```text
20 passed in 0.17s
```

Canonical contract checks passed on the same run. Downstream `Integration / Chat 4 -> Chat 5` remains an acceptance gate for the final handoff.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- normalized/query-optimized production database schema;
- migration framework;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis;
- shared contract expansion for physical events.
