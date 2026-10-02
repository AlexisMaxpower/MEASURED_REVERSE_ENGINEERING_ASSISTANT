# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-02**
- Branch: `chat-5/pass-19`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 19**
- Orchestration directive: `OD-2026-10-02-011`
- Shared baseline at worker start: `main` @ `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`
- Tested implementation SHA: `235dd415eeb7138ae0bc60aa3f2f91b6f8e440ed`
- MREA CI: `36951782512` — **SUCCESS**
- Chat 5 / Lifecycle: **103 passed in 3.83s**
- Contracts / canonical fixtures: **SUCCESS**
- Chat 4 / Generic CAD gate: **SUCCESS**
- Integration / Chat 4 -> Chat 5: **SUCCESS**
- State: **Pass 19 implementation verified; final handoff/freeze pending**

## Baseline discipline

Round 18 was closed and integrated before Pass 19 started. The worker branch was created directly from current shared `main` @ `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`, as required by `OD-2026-10-02-011`.

No historical Pass-18 worker or integration branch was used as the implementation base.

The accepted baseline already includes the final Round-18 field-status integrity repairs performed during orchestration: event-vocabulary validation, legal state-machine transition replay, explicit `TESTED` outcome validation and activation only after persisted `TESTED/PASSED`.

No files outside `chat_5_lifecycle_engineering_knowledge/` are changed by Pass 19.

## Gap closed

Pass 18 intentionally delivered durable physical field status as a Python/read-model surface first. Consumers of the HTTP adapter still had to fetch the whole physical timeline and reconstruct current-state semantics themselves.

Pass 19 closes that transport gap by exposing the accepted projection directly, following the same projection-first/transport-second pattern used for revision-change explanation in Pass 16–17.

## Delivered surface

Added additive transport module:

- `src/mrea_lifecycle/field_status_http.py`;
- `PhysicalFieldStatusLifecycleHttpAPI`;
- `PHYSICAL_FIELD_STATUS_ROUTE`;
- top-level `build_read_only_lifecycle_http_app(...)` now returns the additive adapter.

New route:

```text
GET /v1/lifecycle/physical-field-status?instance_id=<id>
```

The route performs one guarded read-only session call to:

```text
get_physical_field_status(session.queries, instance_id)
```

It serializes the existing `PhysicalFieldStatus` through the existing deterministic JSON response machinery. It does not implement an independent state machine or secondary lifecycle read path.

## Delegation boundary

Every pre-existing HTTP route is delegated to the accepted base `ReadOnlyLifecycleHttpAPI` unchanged.

The existing API schema remains:

```text
mrea.lifecycle-http.v1
```

Cursor signing/verification configuration is reused from the accepted builder; no cursor format or authentication behavior changes.

## Fail-closed HTTP boundary

The field-status route returns:

- missing/blank/unknown instance -> `400 invalid_request`;
- unexpected parameters -> `400 invalid_request`;
- non-GET -> `405 method_not_allowed`;
- stale guarded snapshot -> `409 read_model_stale`;
- `LifecycleKnowledgeIntegrityError` -> `409 read_model_integrity_error`;
- unavailable read model -> `503 read_model_unavailable`.

A durable state-machine contradiction therefore cannot be serialized as a plausible status and cannot escape as an unstructured application error.

## Integrity regression

`tests/test_physical_field_status_http.py` covers:

1. deterministic HTTP serialization of exact committed ACTIVE state;
2. exact source event ID/sequence and persisted location/linkage facts;
3. missing/unknown/unexpected request rejection;
4. GET-only method boundary;
5. deliberate normalized-read-model corruption producing an impossible `MANUFACTURED -> ACTIVATED` transition;
6. explicit `409 read_model_integrity_error` for that corruption;
7. delegation of an existing `/v1/lifecycle/physical-timeline` route through the additive adapter.

## Non-inference boundary

Pass 19 does not:

- mutate lifecycle history;
- infer occupancy beyond latest persisted event context;
- parse free text into state;
- infer causes;
- rank or recommend revisions;
- promote CAD/runtime truth;
- synthesize geometry;
- add semantic search, embeddings or LLM behavior.

## Compatibility

Unchanged:

- `core/contracts/**` and canonical fixtures;
- authoritative SQLite snapshot schema;
- normalized relational schema;
- lifecycle transition semantics;
- manufacturing eligibility;
- cursor formats/authentication;
- existing HTTP response shapes;
- Chat 1–4 code;
- workflow definitions.

## Pass 19 delta before freeze

- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `docs/PASS_19_PHYSICAL_FIELD_STATUS_HTTP.md`;
- `src/mrea_lifecycle/__init__.py`;
- `src/mrea_lifecycle/field_status_http.py`;
- `tests/test_physical_field_status_http.py`.

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation. After that commit the branch is frozen and exact-head CI is verified without another worker change.
