# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 10 authenticated HTTP cursors implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 + orchestration addendum v0.2**  
Запуск Pass 10: **direct user instruction; newer Chat-5-specific directive was absent on `main`**  
Рабочая ветка: `chat-5/pass-10`  
База ветки: `07b9b768404436707575869e7188e0392a021ba5` (frozen Pass 9 handoff)

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

Added dependency-free GET-only WSGI transport with:

- verified `SQLiteLifecycleReadOnlySession` per successful request;
- strict route/query validation;
- deterministic JSON;
- stale read model → `409`;
- unavailable/invalid database → `503`;
- no writable endpoints.

HTTP API schema:

```text
mrea.lifecycle-http.v1
```

### Pass 10

Added optional HMAC-SHA256 authentication for pagination cursors crossing the HTTP boundary.

Authenticated cursor format:

```text
mrea.http-cursor.v1
```

Configuration example:

```python
from mrea_lifecycle import build_read_only_lifecycle_http_app

app = build_read_only_lifecycle_http_app(
    "lifecycle.db",
    cursor_signing_key=secret_key,
    cursor_key_id="2026-09-primary",
)
```

Guarantees:

- minimum 32-byte binary signing key;
- HMAC-SHA256;
- constant-time MAC comparison;
- key identifiers;
- previous-key verification during rotation;
- newly emitted cursors always use the active key;
- tampered, malformed, unknown-key and wrong-key cursors fail closed;
- underlying Pass-8 query/snapshot binding is preserved;
- unsigned Pass-9 mode remains available when no signing key is configured.

`GET /health` reports only cursor mode and active key ID, never key material.

## Verification

Pass 10 adds `tests/test_http_cursor_auth.py` for primitive, HTTP integration, tampering, wrong-key handling, key rotation, query binding, snapshot binding and backward compatibility.

GitHub-hosted implementation and cross-slice gates are checked on the current Pass-10 branch before final handoff.

## Documentation

- `docs/PASS_3_PHYSICAL_PART_INSTANCE_LIFECYCLE.md`
- `docs/PASS_4_PERSISTENCE_UOW.md`
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`
- `docs/PASS_7_ENGINEERING_KNOWLEDGE_QUERIES.md`
- `docs/PASS_8_KNOWLEDGE_PAGINATION.md`
- `docs/PASS_9_READ_ONLY_HTTP_API.md`
- `docs/PASS_10_AUTHENTICATED_HTTP_CURSORS.md`
- `docs/IMPLEMENTATION_STATE.md`
- `ORCHESTRATOR_HANDOFF.md`

## Still intentionally out of scope

- client authentication and authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- keyset pagination for very large datasets;
- materialized analytical aggregates;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.

Pass 10 authenticates pagination cursors only; it does not by itself make the API an Internet-facing security boundary.
