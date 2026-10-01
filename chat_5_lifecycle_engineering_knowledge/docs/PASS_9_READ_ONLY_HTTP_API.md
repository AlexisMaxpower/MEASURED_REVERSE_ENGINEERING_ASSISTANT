# Pass 9 — Read-Only HTTP/API Transport

## Authorization and base

Pass 9 was started by direct user instruction after Pass 8 was frozen.

At branch start, repository `main` still exposed Chat 5 directive `OD-2026-09-29-003`; no newer Chat-5-specific directive was available. Pass 9 therefore starts from the exact frozen Pass 8 head:

```text
82e2203aaeb69ee1fe9f89fd42d0aea451b8690f
```

No shared contract, canonical fixture, CI workflow, integration test, SQLite migration, or other chat-owned file is modified.

## Goal

Expose the committed lifecycle and engineering knowledge read surface through a real HTTP contract without weakening the read-only, snapshot-consistency, cursor-integrity or ownership guarantees established in Passes 5-8.

The transport invariant is:

```text
HTTP GET
→ strict route + query validation
→ fresh SQLiteLifecycleReadOnlySession
→ existing SQL/knowledge query
→ deterministic JSON
```

There are no write routes.

## Dependency decision

Pass 9 intentionally does **not** add FastAPI, Flask or another web framework.

Reason:

- Chat 5 CI currently installs only Python + pytest;
- changing repository-wide CI/dependency policy is not owned by Chat 5;
- the transport boundary can be implemented and tested with Python's WSGI standard;
- a later application shell can mount the same WSGI app directly or adapt the same service contract into another framework.

Implementation uses only Python standard-library HTTP/serialization primitives plus existing Chat-5 modules.

## API schema version

```text
mrea.lifecycle-http.v1
```

Successful response envelope:

```json
{
  "schema_version": "mrea.lifecycle-http.v1",
  "snapshot_version": 12,
  "data": {}
}
```

Error response envelope:

```json
{
  "schema_version": "mrea.lifecycle-http.v1",
  "error": {
    "code": "invalid_request",
    "message": "..."
  }
}
```

JSON uses deterministic key ordering and compact separators.

## Transport implementation

Added `src/mrea_lifecycle/http_api.py` with:

- `ReadOnlyLifecycleHttpAPI`;
- `build_read_only_lifecycle_http_app()`;
- `LifecycleHttpResponse`;
- `LifecycleHttpRequestError`;
- `LifecycleHttpNotFoundError`;
- `LifecycleHttpMethodNotAllowedError`;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION`.

The app is a WSGI callable and can also be exercised directly through `dispatch()`.

## Routes

### Health

```text
GET /health
```

Returns:

- authoritative snapshot version;
- read-model version;
- relational schema version;
- `read_only = true`.

### SQL-native lifecycle queries

```text
GET /v1/lifecycle/revisions?part_id=...
GET /v1/lifecycle/failures?revision_id=...&instance_id=...
GET /v1/lifecycle/equipment-occupancy?equipment_id=...&position=...
GET /v1/lifecycle/physical-timeline?instance_id=...
```

`revision_id` or `instance_id` is required for failure history.

### Engineering knowledge queries

```text
GET /v1/knowledge/revision-lineage?part_id=...
GET /v1/knowledge/revision-outcomes?part_id=...&limit=...&cursor=...
GET /v1/knowledge/equipment-history?equipment_id=...&position=...&event_type=...&revision_id=...&instance_id=...&limit=...&cursor=...
GET /v1/knowledge/failure-patterns?part_id=...&revision_id=...&limit=...&cursor=...
GET /v1/knowledge/replacement-chain?instance_id=...
```

Pass-8 cursor semantics are preserved exactly. Cursor values are not decoded or reinterpreted by the HTTP layer; they are delegated to the knowledge layer.

## Fail-closed request contract

The transport rejects:

- every method except GET;
- unknown routes;
- unknown query parameters;
- duplicate query parameters;
- missing required identifiers;
- blank required identifiers;
- non-integer limits;
- invalid limits;
- invalid/tampered/query-mismatched/stale cursors.

This avoids accepting ambiguous request shapes.

## Status mapping

```text
200  successful read
400  invalid request or invalid cursor
404  unknown route
405  non-GET method
409  relational read model is stale against authoritative snapshot
503  read-only lifecycle database unavailable/invalid
```

`405` includes:

```text
Allow: GET
```

Every response includes:

```text
Content-Type: application/json; charset=utf-8
Cache-Control: no-store
X-Content-Type-Options: nosniff
```

## Read-only guarantee

Every successful data request creates a fresh `SQLiteLifecycleReadOnlySession`.

That session still opens SQLite using:

```text
mode=ro
PRAGMA query_only = ON
```

and still verifies:

```text
snapshot schema
relational schema
snapshot_version == read_model_version
```

The HTTP adapter has no reference to `SQLiteLifecycleStore`, `LifecycleUnitOfWork` or mutation services in production code.

A POST/PUT/PATCH/DELETE request never reaches a domain service and returns `405`.

## Serialization

The transport recursively serializes:

- dataclass results;
- tuples/lists;
- mappings;
- datetime/date as ISO-8601;
- Enum values;
- Decimal as strings.

This keeps engineering IDs and decimal values lossless in JSON.

## Deterministic verification

Added `tests/test_http_api.py`.

Acceptance coverage verifies:

1. health reports a verified read-only snapshot;
2. all nine lifecycle/knowledge GET routes expose committed facts;
3. Pass-8 pagination cursors round-trip through HTTP;
4. a cursor remains bound to its original query/filter set;
5. POST returns 405 and does not advance the snapshot;
6. duplicate query parameters fail closed;
7. unexpected query parameters fail closed;
8. unknown routes return 404;
9. stale relational projection returns 409;
10. missing database returns 503;
11. identical requests against the same snapshot produce byte-identical JSON.

Independent GitHub-hosted Chat 5 implementation run:

```text
head: 44dc38b040ee5e72248e9554c7bde44bd553632d
MREA CI: 36653295496
Chat 5 / Lifecycle: SUCCESS
46 passed in 1.66s
```

## Backward compatibility

Pass 9 is additive.

Unchanged:

- persistence schema;
- relational schema;
- lifecycle domain;
- physical-instance state machine;
- CAD verification/manufacturing eligibility;
- canonical `mrea.lifecycle-event.v1` adapter;
- Pass-7 knowledge semantics;
- Pass-8 cursor format and behavior;
- existing direct Python query APIs.

## Intentionally still open

- process/server launcher and deployment configuration;
- authentication/authorization for remote network exposure;
- TLS / reverse proxy policy;
- CORS policy;
- authenticated cursor signing across an external trust boundary;
- keyset pagination for very large histories;
- materialized analytical aggregates;
- semantic/AI interpretation;
- field-device synchronization.

The Pass-9 API should be treated as a **local/internal read transport** until authentication and network-exposure policy are defined by the owning integration layer.
