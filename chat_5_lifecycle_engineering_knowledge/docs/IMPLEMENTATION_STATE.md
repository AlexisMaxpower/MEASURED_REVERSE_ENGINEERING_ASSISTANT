# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-02**
- Branch: `chat-5/pass-17`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 17**
- Orchestration directive: `OD-2026-10-02-009`
- Shared baseline at worker start: `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`
- Tested implementation SHA: `803cfb3284e438d072e5fa10664f3a689f3582be`
- MREA CI: `36940876273` — **SUCCESS**
- Chat 5 / Lifecycle: **88 passed in 3.42s**
- Contracts / canonical fixtures: **SUCCESS**
- Chat 4 / Generic CAD gate: **SUCCESS**
- Integration / Chat 4 -> Chat 5: **SUCCESS**
- State: **Pass 17 implementation verified; final handoff/freeze pending**

## Baseline discipline

Round 16 was already closed and integrated when Pass 17 started. The worker branch was created directly from the then-current shared `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`, as required by `OD-2026-10-02-009`.

No historical Pass-15/16 worker or integration branch was used as the implementation base.

No files outside `chat_5_lifecycle_engineering_knowledge/` are changed by Pass 17.

## Gap closed

Pass 16 added deterministic source-backed revision-change explanation as an internal Python knowledge surface. Pass 17 exposes that exact factual explanation through the existing local/internal GET-only HTTP adapter so transport consumers do not need to reconstruct explanation semantics from lower-level comparison payloads.

## Delivered surface

Added route:

```text
GET /v1/knowledge/revision-change-explanation
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

The handler:

1. validates the exact two required query parameters;
2. opens the existing guarded `SQLiteLifecycleReadOnlySession`;
3. calls `explain_revision_changes(session.knowledge, ...)`;
4. serializes the existing `RevisionChangeExplanation` through the existing deterministic JSON serializer;
5. returns the standard `mrea.lifecycle-http.v1` envelope with the accepted snapshot version.

No duplicate comparison/explanation model or secondary read path is introduced.

## Factual evidence preserved over HTTP

Serialized explanation facts retain only already committed Chat-5 evidence:

- revision IDs;
- manufacturing/test/failure record IDs where applicable;
- exact stored test artifact IDs;
- exact stored failure evidence artifact IDs;
- deterministic lifecycle states;
- ordered factual changed categories and fields.

The route does not add ranking, recommendation, score, causal inference, geometry inference or semantic/AI interpretation.

## Fail-closed behavior

Existing HTTP boundaries remain authoritative:

- missing or blank revision IDs -> `400 invalid_request`;
- missing revisions -> `400 invalid_request`;
- cross-part revision pair -> `400 invalid_request`;
- duplicate/unexpected parameters -> `400 invalid_request`;
- non-GET methods -> `405 method_not_allowed`;
- stale read model -> `409 read_model_stale`;
- unavailable read model -> `503 read_model_unavailable`.

The Pass-16 category-integrity guard remains inside the explanation builder and prevents contradictory explanation output.

## Compatibility

Unchanged:

- `core/contracts/**` and canonical fixtures;
- SQLite relational schema and authoritative snapshot schema;
- cursor formats and cursor authentication;
- manufacturing-eligibility rules;
- lifecycle transition semantics;
- Chat 1–4 code;
- workflow definitions;
- existing HTTP routes and response payloads;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION = mrea.lifecycle-http.v1`.

## Pass 17 delta before freeze

- `README.md`;
- `docs/PASS_17_REVISION_CHANGE_EXPLANATION_HTTP.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `src/mrea_lifecycle/http_api.py`;
- `tests/test_revision_change_explanation_http.py`.

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation. After that commit the branch is frozen and exact-head CI is verified without another worker change.
