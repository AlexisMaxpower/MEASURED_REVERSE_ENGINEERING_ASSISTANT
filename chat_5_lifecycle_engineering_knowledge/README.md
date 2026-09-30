# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 9 read-only HTTP/API transport implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 9: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-9`  
База ветки: `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` (frozen Pass 8 handoff)

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
- opaque `mrea.knowledge-cursor.v1` pagination bound to query filters and committed snapshot version.

### Pass 9

Added dependency-free WSGI transport:

```python
from mrea_lifecycle import build_read_only_lifecycle_http_app

app = build_read_only_lifecycle_http_app("lifecycle.db")
```

HTTP API schema:

```text
mrea.lifecycle-http.v1
```

Read routes:

```text
GET /health
GET /v1/lifecycle/revisions
GET /v1/lifecycle/failures
GET /v1/lifecycle/equipment-occupancy
GET /v1/lifecycle/physical-timeline
GET /v1/knowledge/revision-lineage
GET /v1/knowledge/revision-outcomes
GET /v1/knowledge/equipment-history
GET /v1/knowledge/failure-patterns
GET /v1/knowledge/replacement-chain
```

Transport guarantees:

- GET-only;
- fresh `SQLiteLifecycleReadOnlySession` per successful request;
- strict known-route / known-query-parameter validation;
- duplicate query parameters rejected;
- Pass-8 cursor validation preserved;
- stale read model fails closed with `409`;
- missing/invalid database fails closed with `503`;
- deterministic JSON serialization;
- no write service or Unit of Work exposed by the production transport.

No FastAPI/Flask dependency was added. The API uses Python WSGI so Chat 5 does not modify repository-wide dependency/CI policy.

## Verification

Independent GitHub-hosted Chat 5 implementation CI on SHA:

```text
44dc38b040ee5e72248e9554c7bde44bd553632d
```

Result:

```text
46 passed in 1.66s
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
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- public/remote network exposure;
- authentication and authorization;
- TLS / reverse-proxy / CORS policy;
- framework-specific application shell;
- authenticated cursor signing across an external trust boundary;
- keyset pagination for very large datasets;
- materialized analytical aggregates;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
