# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 5 normalized relational persistence/query layer implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 5: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-5`  
База ветки: `81a3c1c63e03fbabbd0da1c8191c5ca7ea13cb01` (frozen Pass 4 handoff)

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

- `LifecycleRepository` persistence port;
- `LifecycleUnitOfWork`;
- nested rollback-capable transactions;
- `SQLiteLifecycleStore`;
- authoritative `mrea.lifecycle-snapshot.v1` durable snapshot;
- stale-writer protection and explicit reload;
- atomic canonical + physical persistence.

### Pass 5

Добавлен нормализованный SQL query layer поверх того же authoritative snapshot:

- `SQLiteSchemaManager` и ordered migration journal;
- relational schema version `2`;
- automatic migration/backfill старых Pass-4 databases;
- normalized lifecycle/CAD/manufacturing/installation/test/failure/physical-event tables;
- deterministic relational indexes;
- `lifecycle_read_model_meta.snapshot_version`;
- automatic repair when relational projection lags behind snapshot;
- snapshot + relational projection commit atomically in one SQLite transaction;
- SQL-native `revision_history`;
- SQL-native `failure_history`;
- SQL-native `equipment_occupancy`;
- SQL-native `physical_timeline`.

## Persistence model

Write path:

```text
LifecycleUnitOfWork
→ authoritative aggregate
→ lifecycle_store snapshot
→ normalized SQL read model
→ read-model snapshot_version
→ COMMIT
```

If projection generation fails, the whole transaction rolls back.

Old Pass-4 databases remain readable. Their snapshot is not rewritten merely because Pass 5 adds relational schema; instead the normalized tables are backfilled from the existing snapshot and stamped with the same snapshot version.

## Query surface

```python
store.queries.revision_history("PART-0042")
store.queries.failure_history(instance_id="PI-001")
store.queries.equipment_occupancy(
    equipment_id="RACK-01",
    position="SLOT-A",
)
store.queries.physical_timeline("PI-001")
```

Queries read committed normalized SQL state rather than scanning the complete in-memory aggregate.

## Shared-contract boundary

No shared MREA contract was changed.

Canonical `mrea.lifecycle-event.v1` remains limited to:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

Physical states, migration metadata and relational projection details remain internal to Chat 5.

## Verification

Independent GitHub-hosted Chat 5 CI on Pass-5 implementation SHA `fc1402132092379c94e59332c2d14bfa1e7a367a`:

```text
25 passed in 1.09s
```

Canonical contract checks passed in the same workflow.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- incremental SQL projection updates instead of deterministic full rebuild per write transaction;
- richer engineering query catalogue;
- backup/restore tooling;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis;
- shared contract expansion for physical-only events.
