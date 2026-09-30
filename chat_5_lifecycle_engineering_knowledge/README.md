# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 10.1 keyset pagination implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 10.1: **direct user instruction; central OD-004 currently selects Pass 8 for Round-4 review**  
Рабочая ветка: `chat-5/pass-10.1`  
База ветки: `8044451abd050f69556c9274aec1a83caefad408` (frozen Pass 10 handoff)

## Назначение области

Chat 5 ведёт инженерную историю ревизии и фактическую жизнь конкретного изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed / Tested / Active
→ Failed / Removed / Superseded
→ deterministic engineering knowledge queries
→ snapshot-bound pagination
→ local/internal read-only HTTP transport
→ optional authenticated HTTP cursor boundary
→ keyset continuation for large row histories
```

## Реализовано

### Pass 1–3

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical LifecycleEvent v1 adapter;
- CAD verification → manufacturing gate;
- PhysicalPartInstance identity/state machine;
- exact evidence linkage;
- removal/replacement/supersession.

### Pass 4–6

- LifecycleRepository + LifecycleUnitOfWork;
- SQLite durable snapshot and atomic rollback;
- stale-writer protection;
- normalized relational schema and migration/backfill;
- SQL-native lifecycle queries;
- verified backup/restore;
- read-only SQLite session.

### Pass 7–8

- deterministic revision lineage and factual outcome summaries;
- equipment/position history;
- recurring exact failure-pattern groups;
- replacement chains;
- fail-closed graph integrity checks;
- snapshot-bound knowledge pagination.

### Pass 9–10

- dependency-free GET-only WSGI transport;
- strict request validation and deterministic JSON;
- optional HMAC-SHA256 cursor authentication;
- key IDs and previous-key verification for rotation;
- query/snapshot binding preserved inside authenticated HTTP cursor.

### Pass 10.1

New keyset cursor format:

```text
mrea.knowledge-cursor.v2
```

New traversals for high-cardinality row histories use ordered continuation keys instead of OFFSET:

```text
revision outcomes:
(created_at, revision_id)

equipment history:
(occurred_at, sequence, event_id)
```

Guarantees:

- `LIMIT` + key predicates on v2 continuation;
- no OFFSET for migrated v2 queries;
- deterministic tie-breaking;
- query/filter fingerprint preserved;
- committed snapshot binding preserved;
- Pass-10 HMAC wrapper works unchanged around v2;
- valid `mrea.knowledge-cursor.v1` cursors remain accepted for legacy traversal continuation.

Runtime integration is additive through `SQLiteKeysetEngineeringKnowledgeRepository`; existing factual knowledge semantics are inherited rather than duplicated.

`failure_patterns_page()` remains v1 offset pagination because it is a grouped aggregate query and requires a separate aggregate-keyset design.

## Orchestration truth

Current `main` directive is `OD-2026-09-30-004` and centrally selects **Pass 8** for Round-4 review. Pass 10.1 is a user-authorized worker continuation; it is **not** claimed as centrally accepted or merged to `main`.

## Verification

GitHub-hosted implementation run on SHA:

```text
e1265ad57bf602b0acd44ed029ed1b6e6ccd6666
```

Result:

```text
57 passed in 1.96s
```

Required canonical contract and `Integration / Chat 4 -> Chat 5` gates are rechecked on the documented pre-handoff state before final branch freeze.

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
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- aggregate keyset pagination for grouped failure patterns;
- client authentication and authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- materialized analytical aggregates;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
