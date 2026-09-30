# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 8 snapshot-bound engineering knowledge pagination implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 8: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-8`  
База ветки: `d9bed012eb8bbcea338522847a46572bb5415026` (frozen Pass 7 handoff)

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
→ bounded snapshot-consistent pages
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

- deterministic revision lineage;
- factual revision outcome summaries;
- equipment/position history;
- exact recurring failure-pattern groups;
- explicit replacement chains;
- fail-closed graph integrity checks.

### Pass 8

Added opaque snapshot-bound knowledge pagination:

```python
page = session.knowledge.revision_outcomes_page(
    "PART-0042",
    limit=100,
)

while page.next_cursor is not None:
    page = session.knowledge.revision_outcomes_page(
        "PART-0042",
        limit=100,
        cursor=page.next_cursor,
    )
```

Cursor guarantees:

```text
format = mrea.knowledge-cursor.v1
query/filter fingerprint must match
cursor snapshot_version must equal current read-only snapshot
checksum must match
limit must be 1..500
```

Paginated surfaces:

- `revision_outcomes_page()`;
- `equipment_position_history_page()`;
- `failure_patterns_page()`.

Equipment history pagination also supports exact filters for:

- position;
- event type;
- revision ID;
- physical instance ID.

`revision_lineage()` and `replacement_chain()` deliberately remain whole-graph/whole-chain integrity operations instead of being split into unsafe partial traversals.

## Backward compatibility

All Pass-7 tuple-returning knowledge queries remain unchanged.

No SQLite migration or shared MREA contract change was needed.

## Verification

Independent GitHub-hosted Chat 5 CI on implementation SHA `1a6803bff00eeaa43ffb18fb18c86695c59403d2`:

```text
40 passed in 1.51s
```

Required canonical contract and `Integration / Chat 4 -> Chat 5` gates are rechecked on the final documented pre-handoff state before branch freeze.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`
- `docs/PASS_7_ENGINEERING_KNOWLEDGE_QUERIES.md`
- `docs/PASS_8_KNOWLEDGE_PAGINATION.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- REST/API transport;
- cryptographically authenticated cursors across an external trust boundary;
- keyset pagination for very large datasets;
- materialized analytical aggregates;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
