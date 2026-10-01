# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 11 aggregate keyset pagination implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 11: **direct user instruction**  
Рабочая ветка: `chat-5/pass-11`  
Центральный baseline: текущий `main` `c034f7583d4e1f130f827d94a43762f3cad1a7e5`

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
→ local/internal read-only HTTP transport
→ optional authenticated HTTP cursor boundary
```

## Актуальная cumulative линия

Pass 11 собран file-level replay поверх текущего `main`, а не продолжением stale shared ancestry.

В него сведены:

- cumulative Chat-5 state Pass 3–10.1;
- corrected Round-4 runtime truth из `chat-5/pass-8`;
- Pass-11 aggregate keyset pagination.

`chat-5/pass-8` не изменён.

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

- canonical numerical CAD verification remains independent from runtime evidence;
- runtime `VERIFIED | FAILED | UNVERIFIED` survives persistence/read model;
- runtime-gated manufacturing eligibility fails closed;
- numerical VERIFIED never upgrades runtime UNVERIFIED.

### Engineering knowledge

- revision lineage/outcomes;
- equipment/position history;
- exact failure-pattern groups;
- replacement chains;
- snapshot/query-bound pagination;
- GET-only WSGI read transport;
- optional HMAC-SHA256 cursor authentication.

### Keyset pagination

`mrea.knowledge-cursor.v2` is used by new traversals for:

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

New v2 continuation uses key predicates + `LIMIT`, not OFFSET.

Already-issued v1 cursors remain accepted and continue on their historical OFFSET paths.

## Orchestration truth

Current `main` still carries `OD-2026-09-30-004` and centrally selects corrected Pass 8 for Round-4 handling. Pass 11 is a direct-user-authorized worker continuation and is not represented as centrally accepted or merged.

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
- `docs/BUILD_REUSE_CHECK_PASS11_FAILURE_PATTERN_KEYSET.md`
- `docs/PASS_11_FAILURE_PATTERN_KEYSET_PAGINATION.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- materialized analytical aggregates;
- client authentication/authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
