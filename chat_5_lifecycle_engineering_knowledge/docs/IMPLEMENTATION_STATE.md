# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-30**
- Branch: `chat-5/pass-9`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 9 authorization: **direct user instruction; no newer Chat-5-specific directive present on `main` at branch start**
- Base SHA: `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` (frozen Chat 5 Pass 8)
- State: **read-only HTTP/API transport implemented; final cross-slice gates and handoff pending**

## Preserved baseline

Still active and unchanged:

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical CADPackage + CADVerificationReport transfer;
- VERIFIED manufacturing eligibility gate;
- canonical `LifecycleEvent v1` adapter;
- physical-instance state machine;
- exact instance/evidence linkage;
- equipment/position occupancy protection;
- removal/replacement/supersession semantics;
- LifecycleRepository + LifecycleUnitOfWork;
- authoritative SQLite snapshot;
- normalized relational read model and migrations;
- SQL-native lifecycle queries;
- verified backup/restore;
- read-only SQLite query session;
- deterministic engineering knowledge queries;
- snapshot-bound knowledge pagination.

No shared contract, canonical fixture, CI workflow, integration test, SQLite migration, or other chat-owned file was changed.

## Pass 9 additions

### Read-only HTTP transport

Added `src/mrea_lifecycle/http_api.py`.

Public surface:

- `ReadOnlyLifecycleHttpAPI`;
- `build_read_only_lifecycle_http_app()`;
- `LifecycleHttpResponse`;
- `LifecycleHttpRequestError`;
- `LifecycleHttpNotFoundError`;
- `LifecycleHttpMethodNotAllowedError`;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION = mrea.lifecycle-http.v1`.

The adapter is a dependency-free WSGI callable.

### Dependency boundary

No FastAPI/Flask dependency was introduced.

Reason:

- current Chat 5 CI installs Python + pytest only;
- shared dependency/CI policy is outside Chat 5 ownership;
- WSGI provides a real HTTP boundary using Python standard library only.

### Exposed routes

Health:

```text
GET /health
```

SQL-native lifecycle read routes:

```text
GET /v1/lifecycle/revisions
GET /v1/lifecycle/failures
GET /v1/lifecycle/equipment-occupancy
GET /v1/lifecycle/physical-timeline
```

Engineering knowledge routes:

```text
GET /v1/knowledge/revision-lineage
GET /v1/knowledge/revision-outcomes
GET /v1/knowledge/equipment-history
GET /v1/knowledge/failure-patterns
GET /v1/knowledge/replacement-chain
```

### Request validation

Transport fails closed for:

- non-GET methods;
- unknown routes;
- unknown parameters;
- duplicate parameters;
- missing/blank required identifiers;
- non-integer limits;
- invalid limits;
- invalid/tampered/query-mismatched/stale cursors.

### Status contract

```text
200 success
400 invalid request / cursor
404 route not found
405 method not allowed
409 read model stale
503 read model unavailable
```

`405` includes `Allow: GET`.

All responses include JSON content type, `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

### Read-only invariant

Every successful data request opens a fresh `SQLiteLifecycleReadOnlySession`.

The existing session still enforces:

```text
SQLite mode=ro
PRAGMA query_only = ON
snapshot schema check
relational schema check
snapshot_version == read_model_version
```

Production HTTP code does not import `SQLiteLifecycleStore`, mutation services or `LifecycleUnitOfWork`.

### Deterministic JSON

Serialization supports:

- dataclasses;
- mappings;
- tuples/lists;
- datetime/date as ISO-8601;
- Enum values;
- Decimal as strings.

Keys are sorted and compact separators are used, giving byte-identical JSON for identical requests against the same snapshot.

## Backward compatibility

Pass 9 is additive.

Unchanged:

- direct Python lifecycle queries;
- direct engineering knowledge queries;
- Pass-8 cursor format and semantics;
- persistence and relational schemas;
- lifecycle state transitions;
- CAD verification/manufacturing eligibility;
- canonical shared contracts.

## Verification

### New tests

Added `tests/test_http_api.py`.

Coverage verifies:

1. health reports verified read-only state;
2. all nine read routes return committed facts;
3. pagination cursor round-trips through HTTP;
4. query-bound cursor mismatch returns 400;
5. POST returns 405;
6. rejected write attempt does not advance snapshot version;
7. duplicate parameters fail closed;
8. unexpected parameters fail closed;
9. unknown route returns 404;
10. stale read model returns 409;
11. missing database returns 503;
12. repeated identical requests return byte-identical JSON.

### GitHub-hosted implementation run

Implementation SHA:

```text
44dc38b040ee5e72248e9554c7bde44bd553632d
```

Workflow:

```text
MREA CI / 36653295496
```

Chat 5 result:

```text
46 passed in 1.66s
```

Status: **SUCCESS**.

Required cross-slice gates are rechecked on the documented pre-handoff SHA before `ORCHESTRATOR_HANDOFF.md` is published.

## Files added in Pass 9

- `src/mrea_lifecycle/http_api.py`;
- `tests/test_http_api.py`;
- `docs/PASS_9_READ_ONLY_HTTP_API.md`.

## Files modified in Pass 9

- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Known limitations

Still open:

- public/remote network exposure;
- authentication/authorization;
- TLS/reverse-proxy/CORS policy;
- framework-specific application shell;
- authenticated cursor signing across external trust boundaries;
- keyset pagination for very large histories;
- materialized analytical aggregates;
- semantic/AI interpretation;
- field-device synchronization.

Pass 9 transport is therefore a **local/internal read API**, not an Internet-facing security boundary.

## Handoff rule

After `ORCHESTRATOR_HANDOFF.md` is published as the final worker commit, `chat-5/pass-9` is frozen. No later commit is allowed unless final verification finds a real missing/incorrect GitHub file or Chat 6 explicitly requests a correction.
