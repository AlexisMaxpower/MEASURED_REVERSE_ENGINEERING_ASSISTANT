# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 7 deterministic engineering knowledge queries implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 7: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-7`  
База ветки: `68791080a5440c6426ef28329302c99a323344b0` (frozen Pass 6 handoff)

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
→ deterministic engineering knowledge queries
```

## Реализовано

### Pass 1–3

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical LifecycleEvent v1 adapter;
- CAD verification → manufacturing gate;
- PhysicalPartInstance identity/state machine;
- exact installation/test/failure evidence linkage;
- removal/replacement/supersession.

### Pass 4–6

- LifecycleRepository + LifecycleUnitOfWork;
- SQLite durable snapshot and atomic rollback;
- stale-writer protection;
- normalized relational schema and migration/backfill;
- SQL-native lifecycle queries;
- verified backup/restore;
- read-only SQLite session.

### Pass 7

Added `SQLiteEngineeringKnowledgeRepository`, exposed as:

```python
with SQLiteLifecycleReadOnlySession("lifecycle.db") as session:
    session.knowledge.revision_lineage("PART-0042")
    session.knowledge.revision_outcomes("PART-0042")
    session.knowledge.equipment_position_history(
        equipment_id="RACK-01",
        position="LEFT",
    )
    session.knowledge.failure_patterns(part_id="PART-0042")
    session.knowledge.replacement_chain("PI-001")
```

Queries are deterministic and factual only.

They return:

- revision ancestry and lineage depth;
- per-revision manufacturing/instance/activation/failure/removal/supersession counts;
- complete equipment/position history;
- recurring exact failure-pattern groups;
- explicit physical replacement chains.

They do **not**:

- infer an unrecorded root cause;
- rank revisions as better/worse;
- recommend design changes;
- convert estimated cause into confirmed cause;
- use AI-generated conclusions.

## Integrity behavior

The knowledge layer fails closed when structured facts are inconsistent, including:

- cyclic revision ancestry;
- missing revision parent;
- cyclic replacement chain;
- replacement link to a missing physical instance;
- physical instance without a valid state.

No new SQLite migration was needed in Pass 7 because Pass 5 already normalized all required lifecycle facts.

## Read-only guarantee

Engineering knowledge is exposed through the same Pass-6 `SQLiteLifecycleReadOnlySession`:

```text
SQLite URI mode=ro
PRAGMA query_only = ON
snapshot_version == read_model_version
```

Knowledge queries cannot mutate or repair the lifecycle database.

## Shared-contract boundary

No shared MREA contract was changed.

Canonical `mrea.lifecycle-event.v1` remains limited to:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

Knowledge summaries are internal Chat 5 projections over committed facts.

## Verification

GitHub-hosted Chat 5 CI on implementation SHA `adca8d3dd60b2c727689c9969d4d0ba0d8178384`:

```text
35 passed in 1.32s
```

Final handoff is published only after required contracts and `Integration / Chat 4 -> Chat 5` gates are green on the final pre-handoff state.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`
- `docs/PASS_7_ENGINEERING_KNOWLEDGE_QUERIES.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- AI / semantic interpretation;
- design recommendations;
- confidence scoring for inferred conclusions;
- REST/API;
- large-history pagination/materialized analytical aggregates;
- field-device synchronization;
- shared contract expansion for physical-only events.
