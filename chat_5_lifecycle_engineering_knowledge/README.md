# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 12 materialized engineering aggregates implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 12: **direct user instruction**  
Рабочая ветка: `chat-5/pass-12`  
Центральный baseline Pass 12: `main` @ `c888704b37e88b68c055f1095e6e9a4fc3650f7e`

## Назначение области

Chat 5 ведёт инженерную историю ревизии и фактическую жизнь конкретного изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed / Tested / Active
→ Failed / Removed / Superseded
→ deterministic engineering knowledge queries
→ snapshot-bound keyset pagination
→ materialized analytical read model
→ local/internal read-only HTTP transport
→ optional authenticated HTTP cursor boundary
```

## Актуальная orchestration truth

Pass 11 уже интегрирован центральным оркестратором и закрыт в `main` как часть Round 11. Pass 12 начат непосредственно от текущего общего baseline `c888704b...`; старое worker-local утверждение о том, что Pass 11 не merged, больше не является актуальным.

Pass 12 не меняет shared contracts, Chat 1–4, root integration tests или workflows.

## Реализовано

### Lifecycle / persistence

- Revision / Manufacturing / Installation / Test / Failure domain;
- PhysicalPartInstance identity/state machine;
- exact failure/evidence linkage;
- lifecycle repository + unit of work;
- SQLite authoritative snapshot;
- normalized relational read model;
- backup/restore and read-only session.

### CAD → lifecycle truth

- canonical numerical CAD verification остаётся независимой от runtime evidence;
- runtime `VERIFIED | FAILED | UNVERIFIED` переживает persistence/read model;
- runtime-gated manufacturing eligibility fail-closed;
- numerical VERIFIED никогда не повышает runtime UNVERIFIED до VERIFIED.

### Engineering knowledge

- revision lineage/outcomes;
- equipment/position history;
- exact failure-pattern groups;
- replacement chains;
- snapshot/query-bound pagination;
- GET-only WSGI read transport;
- optional HMAC-SHA256 cursor authentication.

### Keyset pagination

`mrea.knowledge-cursor.v2` используется новыми traversal для:

```text
revision outcomes:
(created_at, revision_id)

equipment history:
(occurred_at, sequence, event_id)

failure patterns:
(occurrence_count DESC,
 failure_type,
 damage_location,
 cause_null_rank,
 cause_sort)
```

Новые v2 continuation используют key predicates + `LIMIT`, не OFFSET. Уже выданные v1 cursors остаются совместимыми и продолжают исторический OFFSET path.

### Pass 12 — materialized analytical read model

SQLite relational schema поднята до version `4`.

Материализованы два существующих дорогих factual aggregate:

- `lifecycle_revision_outcomes_materialized`;
- `lifecycle_failure_patterns_materialized`.

Они не вводят новую предметную семантику: содержимое строится из уже существующего normalized read model и проверяется на равенство прежним raw aggregate queries.

Refresh происходит внутри той же SQLite transaction, что и публикация нового `lifecycle_read_model_meta.snapshot_version`. Поэтому reader либо видит старый полностью согласованный committed snapshot, либо новый полностью согласованный snapshot; промежуточное состояние не публикуется.

`SQLiteLifecycleReadOnlySession` теперь выдаёт `SQLiteMaterializedEngineeringKnowledgeRepository`:

- direct revision-outcome/failure-pattern reads идут по materialized tables;
- v2 pages идут по materialized tables + keyset predicates;
- legacy v1 pages намеренно делегируются историческому raw OFFSET path для cursor continuity;
- equipment history и остальные factual queries сохраняют прежний implementation path.

## Проверка Pass 12

Tested implementation SHA:

```text
0e4b2df0b144fe7116b7e94141be85266a0820fc
```

MREA CI:

```text
36802306777 — SUCCESS
Chat 5 / Lifecycle: 72 passed in 11.64s
Contracts / canonical fixtures: SUCCESS
Chat 4 / Generic CAD gate: SUCCESS
Integration / Chat 4 -> Chat 5: SUCCESS
```

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`
- `docs/PASS_7_ENGINEERING_KNOWLEDGE_QUERIES.md`
- `docs/PASS_8_KNOWLEDGE_PAGINATION.md`
- `docs/PASS_9_READ_ONLY_HTTP_API.md`
- `docs/PASS_10_AUTHENTICATED_HTTP_CURSORS.md`
- `docs/PASS_10_1_KEYSET_PAGINATION.md`
- `docs/PASS_11_FAILURE_PATTERN_KEYSET_PAGINATION.md`
- `docs/BUILD_REUSE_CHECK_PASS12_MATERIALIZED_KNOWLEDGE.md`
- `docs/PASS_12_MATERIALIZED_ANALYTICAL_AGGREGATES.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- client authentication/authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
