# ORCHESTRATOR HANDOFF — Chat 5 / Pass 9

**Authorization:** direct user instruction to continue development  
**Orchestrator status at branch start:** no newer Chat-5-specific directive was present on `main`; `ORCHESTRATOR_DIRECTIVE.md` still reported `OD-2026-09-29-003`  
**Branch:** `chat-5/pass-9`  
**Base SHA:** `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` — frozen Chat 5 Pass 8  
**Independently tested implementation SHA:** `44dc38b040ee5e72248e9554c7bde44bd553632d`  
**Documented pre-handoff SHA:** `c51facd33096aecc810b9aeec742c3f4bb3a5866`  
**Pre-handoff CI run:** `36653464430`  
**Status at handoff:** required Chat 5 gates GREEN

> This handoff is the final worker commit and freezes `chat-5/pass-9`. Chat 6 should use the current branch head as the final handoff commit. The documented pre-handoff SHA above is the exact implementation/documentation state exercised by the required gates.

## 1. Delivered functionality

Pass 9 adds a dependency-free **read-only HTTP/API transport** over the committed lifecycle and engineering knowledge read model.

Transport chain:

```text
HTTP GET
→ strict route/query validation
→ fresh SQLiteLifecycleReadOnlySession
→ existing SQL/knowledge query
→ deterministic JSON
```

There are no write routes.

## 2. API version

```text
mrea.lifecycle-http.v1
```

Success envelope:

```json
{
  "schema_version": "mrea.lifecycle-http.v1",
  "snapshot_version": 12,
  "data": {}
}
```

Error envelope:

```json
{
  "schema_version": "mrea.lifecycle-http.v1",
  "error": {
    "code": "invalid_request",
    "message": "..."
  }
}
```

## 3. Transport implementation

Added `src/mrea_lifecycle/http_api.py` with:

- `ReadOnlyLifecycleHttpAPI`;
- `build_read_only_lifecycle_http_app()`;
- `LifecycleHttpResponse`;
- `LifecycleHttpRequestError`;
- `LifecycleHttpNotFoundError`;
- `LifecycleHttpMethodNotAllowedError`;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION`.

The app is a WSGI callable and may also be exercised through `dispatch()`.

## 4. Routes

Health:

```text
GET /health
```

SQL-native lifecycle reads:

```text
GET /v1/lifecycle/revisions?part_id=...
GET /v1/lifecycle/failures?revision_id=...&instance_id=...
GET /v1/lifecycle/equipment-occupancy?equipment_id=...&position=...
GET /v1/lifecycle/physical-timeline?instance_id=...
```

Engineering knowledge reads:

```text
GET /v1/knowledge/revision-lineage?part_id=...
GET /v1/knowledge/revision-outcomes?part_id=...&limit=...&cursor=...
GET /v1/knowledge/equipment-history?equipment_id=...&position=...&event_type=...&revision_id=...&instance_id=...&limit=...&cursor=...
GET /v1/knowledge/failure-patterns?part_id=...&revision_id=...&limit=...&cursor=...
GET /v1/knowledge/replacement-chain?instance_id=...
```

Pass-8 cursor semantics are delegated unchanged to the knowledge layer.

## 5. Fail-closed HTTP contract

Rejected:

- all methods except GET;
- unknown routes;
- unknown query parameters;
- duplicate query parameters;
- missing or blank required identifiers;
- malformed/invalid page limits;
- invalid, tampered, query-mismatched or stale cursors.

Status mapping:

```text
200 success
400 invalid request/cursor
404 route not found
405 method not allowed
409 relational read model stale
503 read model unavailable
```

`405` returns `Allow: GET`.

All responses use JSON and include:

```text
Cache-Control: no-store
X-Content-Type-Options: nosniff
```

## 6. Read-only guarantee

Every successful data request opens a fresh `SQLiteLifecycleReadOnlySession`.

Existing guarantees remain authoritative:

```text
SQLite mode=ro
PRAGMA query_only = ON
snapshot schema validation
relational schema validation
snapshot_version == read_model_version
```

Production HTTP code does not import `SQLiteLifecycleStore`, `LifecycleUnitOfWork` or mutation services.

A rejected POST request was tested not to advance the committed snapshot version.

## 7. Dependency decision

No FastAPI, Flask or new external package was introduced.

Reason:

- current Chat-5 CI installs only Python + pytest;
- repository-wide dependency/CI policy is outside Chat-5 ownership;
- WSGI supplies a real testable HTTP contract with the Python standard library.

A future application shell may mount or adapt this transport without changing the underlying read model.

## 8. Deterministic serialization

Transport serializes:

- dataclasses;
- mappings;
- tuples/lists;
- datetime/date as ISO-8601;
- Enum values;
- Decimal as strings.

JSON keys are sorted and compact separators are used. Identical requests against the same snapshot are verified byte-identical.

## 9. Files changed in Pass 9

Added:

- `src/mrea_lifecycle/http_api.py`;
- `tests/test_http_api.py`;
- `docs/PASS_9_READ_ONLY_HTTP_API.md`.

Modified:

- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md`.

No Pass-9 file outside `chat_5_lifecycle_engineering_knowledge/` was modified.

## 10. Acceptance tests

`tests/test_http_api.py` verifies:

1. health reports verified read-only state;
2. all nine read routes expose committed facts;
3. pagination cursor round-trips through HTTP;
4. query-bound cursor mismatch fails closed;
5. POST returns 405;
6. rejected write attempt leaves snapshot unchanged;
7. duplicate query parameters fail closed;
8. unexpected parameters fail closed;
9. unknown route returns 404;
10. stale relational projection returns 409;
11. missing database returns 503;
12. identical requests against one snapshot return byte-identical JSON.

## 11. Independent CI evidence

Implementation run:

```text
head: 44dc38b040ee5e72248e9554c7bde44bd553632d
MREA CI / 36653295496
Chat 5 / Lifecycle — SUCCESS
46 passed in 1.66s
```

Documented pre-handoff run:

```text
head: c51facd33096aecc810b9aeec742c3f4bb3a5866
MREA CI / 36653464430
```

Required results:

- `Chat 5 / Lifecycle` — **SUCCESS**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**.

## 12. Backward compatibility

Unchanged:

- lifecycle domain and physical-instance state machine;
- SQLite persistence/relational schemas;
- CAD verification/manufacturing eligibility;
- canonical `mrea.lifecycle-event.v1`;
- Pass-7 engineering knowledge semantics;
- Pass-8 `mrea.knowledge-cursor.v1` semantics;
- all existing direct Python query APIs.

No shared contract change request was required.

## 13. Ownership verification

Pre-handoff diff against frozen Pass 8 base `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` contained exactly six files, all under Chat 5 ownership.

This handoff is the seventh changed file.

No Pass-9 changes were made to:

- `core/contracts/`;
- canonical fixtures;
- `.github/workflows/`;
- `tests/integration/`;
- Chat 1-4;
- Chat 6 files.

## 14. Known limitations

Still intentionally open:

- public/remote network exposure;
- authentication/authorization;
- TLS/reverse-proxy/CORS policy;
- framework-specific application shell;
- authenticated cursor signing across an external trust boundary;
- keyset pagination for very large histories;
- materialized analytical aggregates;
- semantic/AI interpretation;
- field-device synchronization.

Pass 9 is therefore a **local/internal read API**, not an Internet-facing security boundary.

## 15. Requested acceptance gate

Please verify:

1. production transport exposes no write route;
2. every successful request uses the verified read-only session;
3. stale read model fails closed;
4. strict route/query validation is preserved;
5. Pass-8 cursors retain snapshot/query binding through HTTP;
6. deterministic JSON is stable for the same snapshot;
7. direct Python APIs remain unchanged;
8. canonical lifecycle/CAD eligibility behavior remains unchanged;
9. required CI gates are green;
10. ownership boundaries are preserved;
11. Chat 6 reconciles the direct-user Pass-9 branch base during central integration.

Requested verdict: **Pass 9 ACCEPTED, ACCEPTED_WITH_REBASE/INTEGRATION FOLLOWUP, or explicit FIX_REQUIRED.**
