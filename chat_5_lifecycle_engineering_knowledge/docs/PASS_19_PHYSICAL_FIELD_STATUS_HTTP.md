# Chat 5 Pass 19 — Physical Field Status HTTP

## Goal

Pass 18 established a durable, deterministic `PhysicalFieldStatus` projection over one committed physical-instance timeline. Pass 19 exposes that accepted projection through the existing local/internal GET-only HTTP boundary without duplicating lifecycle semantics.

## Baseline

- orchestration directive: `OD-2026-10-02-011`;
- Round 18 closed and integrated;
- worker baseline: `main` @ `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`;
- Pass 19 branch: `chat-5/pass-19`.

The baseline already contains the final Round-18 integrity repairs: full physical event vocabulary validation, legal transition replay, mandatory `TESTED` outcome validation and `ACTIVATED` only after persisted `TESTED/PASSED`.

## Delivered route

```text
GET /v1/lifecycle/physical-field-status?instance_id=<id>
```

The top-level `build_read_only_lifecycle_http_app(...)` returns `PhysicalFieldStatusLifecycleHttpAPI`, an additive adapter over the accepted `ReadOnlyLifecycleHttpAPI`.

For the new route it:

1. accepts only GET;
2. accepts exactly one required `instance_id` parameter;
3. opens the existing `SQLiteLifecycleReadOnlySession`;
4. calls `get_physical_field_status(session.queries, instance_id)`;
5. serializes the existing `PhysicalFieldStatus` through the existing deterministic HTTP serializer;
6. returns the existing `mrea.lifecycle-http.v1` envelope with the accepted snapshot version.

Every other route delegates to the accepted base adapter unchanged.

## Returned factual surface

The route exposes only facts already present in the accepted Pass-18 projection:

- physical instance ID;
- revision ID;
- manufacturing ID;
- current physical state;
- exact state-change timestamp;
- exact source event ID and sequence;
- latest persisted installation/test/failure linkage;
- latest persisted equipment/position context;
- latest-event test outcome, replacement ID and notes when present.

No extra inference is performed at the HTTP boundary.

## Fail-closed behavior

```text
missing / blank instance_id        -> 400 invalid_request
unknown instance_id                -> 400 invalid_request
unexpected query parameter         -> 400 invalid_request
non-GET method                     -> 405 method_not_allowed
stale guarded snapshot             -> 409 read_model_stale
corrupt durable lifecycle history  -> 409 read_model_integrity_error
unavailable read model             -> 503 read_model_unavailable
```

`LifecycleKnowledgeIntegrityError` is deliberately not converted into a plausible current state and is not allowed to escape as an unstructured server failure.

## Integrity test

The HTTP regression suite deliberately corrupts the normalized physical-event read model after a valid commit by replacing an `INSTALLED` event with `ACTIVATED`. The guarded metadata still identifies the same snapshot generation, so the Pass-18 state-machine replay is the layer that must detect the impossible `MANUFACTURED -> ACTIVATED` transition.

Expected result: `409 read_model_integrity_error`.

This test demonstrates that the transport preserves the projection's fail-closed truth boundary rather than merely testing request syntax.

## Compatibility

Unchanged:

- `core/contracts/**` and canonical fixtures;
- authoritative SQLite snapshot schema;
- normalized relational schema;
- lifecycle transition semantics;
- manufacturing eligibility;
- cursor formats/authentication;
- existing HTTP routes and response shapes;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION = mrea.lifecycle-http.v1`;
- Chat 1–4 code;
- workflow definitions.

No new external dependency is introduced.

## Non-goals

Pass 19 does not add:

- occupancy inference beyond stored latest-event context;
- causal interpretation;
- revision ranking or recommendation;
- geometry inference;
- semantic search or LLM processing;
- field-device synchronization;
- shared contract expansion.

## Verification

Independently tested implementation SHA:

```text
235dd415eeb7138ae0bc60aa3f2f91b6f8e440ed
```

MREA CI:

```text
36951782512 — SUCCESS
```

Key results:

- Chat 5 / Lifecycle: `103 passed`;
- Contracts / canonical fixtures: SUCCESS;
- Chat 4 / Generic CAD gate: SUCCESS;
- Integration / Chat 4 -> Chat 5: SUCCESS.
