# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 6 verified backup/restore + read-only access implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 6: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-6`  
База ветки: `831460686fe3d506cce68ae2b06fd88ea30ea1bc` (frozen Pass 5 handoff)

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

- `SQLiteSchemaManager` + ordered migration journal;
- relational schema version `2`;
- Pass-4-compatible migration/backfill;
- normalized relational lifecycle read model;
- snapshot/read-model version synchronization and self-repair;
- SQL-native revision/failure/equipment/timeline queries.

### Pass 6

Добавлен operational recovery/read layer:

- `LifecycleBackupManager`;
- backup manifest `mrea.lifecycle-backup.v1`;
- native SQLite consistent backup via `sqlite3.Connection.backup()`;
- pre-backup `integrity_check` + `foreign_key_check`;
- requirement `snapshot_version == read_model_version` before backup;
- SHA-256 + byte-size manifest verification;
- verified restore through temporary database + atomic `os.replace()`;
- overwrite protection unless explicitly requested;
- `SQLiteLifecycleReadOnlySession` using SQLite `mode=ro`;
- `PRAGMA query_only = ON`;
- read-only stale-projection rejection;
- explicit reader `refresh()`.

## Persistence / recovery model

Write path remains unchanged from Pass 5:

```text
LifecycleUnitOfWork
→ authoritative aggregate
→ lifecycle_store snapshot
→ normalized SQL read model
→ read-model snapshot_version
→ COMMIT
```

Backup path:

```text
committed lifecycle.db
→ read-only integrity + version inspection
→ SQLite native backup API
→ inspect backup image
→ SHA-256 manifest
→ atomic publish
```

Restore path:

```text
backup + manifest
→ verify hash/size/schema/versions/integrity
→ restore into temp SQLite file
→ inspect restored image
→ atomic replace destination
```

## Read-only query surface

```python
with SQLiteLifecycleReadOnlySession("lifecycle.db") as session:
    session.queries.revision_history("PART-0042")
    session.queries.failure_history(instance_id="PI-001")
    session.queries.equipment_occupancy(equipment_id="RACK-01")
    session.queries.physical_timeline("PI-001")
```

The read-only session never repairs or writes the database. If the normalized projection is stale relative to the authoritative snapshot it fails with `LifecycleReadOnlyStaleError`; repair remains the responsibility of the writable `SQLiteLifecycleStore`.

## Shared-contract boundary

No shared MREA contract was changed.

Canonical `mrea.lifecycle-event.v1` remains limited to:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

Backup manifests, read-only session state, physical states and relational persistence details remain internal to Chat 5.

## Verification

Independent GitHub-hosted Chat 5 CI on Pass-6 implementation/documentation SHA `52ebc6614064c6541c65651a5af58d99bb5e65c4`:

```text
31 passed in 3.73s
```

Canonical contract checks and Chat 4 generic CAD gate passed on the same workflow run. Final handoff is published only after the downstream `Integration / Chat 4 -> Chat 5` gate is green on the final pre-handoff state.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- encrypted/off-host backup transport;
- retention/rotation/scheduled backup orchestration;
- incremental SQL projection updates instead of deterministic full rebuild per write transaction;
- richer engineering knowledge query catalogue;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis;
- shared contract expansion for physical-only events.
