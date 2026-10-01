# Chat 5 — Pass 17: Revision Change Explanation HTTP

## Baseline

- Worker branch: `chat-5/pass-17`
- Required base: shared `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`
- Orchestration directive: `OD-2026-10-02-009`
- Round 16 closure is already integrated in the base.

Pass 17 starts from the current shared `main`; no historical worker or integration branch is used as the implementation baseline.

## Gap closed

Pass 16 created deterministic source-backed revision-change explanation as a Python knowledge surface, but the local/internal GET-only HTTP transport could not expose that explanation. Consumers had to call the Python API directly or reconstruct differences from lower-level comparison payloads.

Pass 17 closes that transport gap without changing the explanation semantics.

## Added route

```text
GET /v1/knowledge/revision-change-explanation
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

The route requires exactly one non-blank `left_revision_id` and `right_revision_id` and rejects unexpected query parameters.

The response uses the existing envelope:

```text
schema_version
snapshot_version
data
```

`data` is the existing `RevisionChangeExplanation` projection and therefore contains only committed deterministic facts:

- `part_id`;
- left/right revision IDs;
- ordered `changed_categories`;
- ordered facts;
- exact source revision IDs;
- exact manufacturing/test/failure record IDs where applicable;
- exact stored artifact/evidence IDs where applicable.

## Snapshot and truth boundary

The HTTP handler opens the same guarded read-only session used by all Chat-5 HTTP knowledge routes and delegates to `explain_revision_changes(...)`.

`explain_revision_changes(...)` reuses one `compare_revision_details(...)` result. Therefore one response cannot mix facts from different accepted snapshot generations.

Existing fail-closed behavior is preserved:

- missing or blank pair parameters -> `400 invalid_request`;
- cross-part revisions -> `400 invalid_request`;
- unknown revisions -> `400 invalid_request`;
- unexpected parameters -> `400 invalid_request`;
- non-GET methods -> `405 method_not_allowed`;
- stale read model -> existing `409 read_model_stale` boundary;
- unavailable read model -> existing `503 read_model_unavailable` boundary.

## Non-inference boundary

The new route does not add any new reasoning layer. It does not:

- rank or score revisions;
- recommend a preferred revision;
- infer a cause from a change/failure correlation;
- promote estimated causes to confirmed causes;
- derive geometry from notes, failures or CAD artifact identifiers;
- use an LLM, embedding, semantic search or heuristic ranking.

It only serializes the exact deterministic Pass-16 explanation.

## Compatibility

Unchanged:

- `core/contracts/**` and canonical fixtures;
- SQLite relational schema version;
- authoritative snapshot schema;
- cursor formats/authentication;
- manufacturing eligibility;
- lifecycle transition semantics;
- Chat 1–4 code;
- workflow definitions;
- `LIFECYCLE_HTTP_API_SCHEMA_VERSION` (`mrea.lifecycle-http.v1`).

The endpoint is additive and existing response payloads are unchanged.

## Regression coverage

`tests/test_revision_change_explanation_http.py` verifies:

- deterministic byte-identical JSON for the same snapshot/query;
- exact record IDs and exact artifact/evidence IDs in serialized sources;
- factual lifecycle-state serialization;
- no fabricated delta for same-revision comparison;
- no geometry/ranking/recommendation fields;
- fail-closed missing, cross-part and unexpected inputs;
- GET-only behavior.

## Build / reuse decision

Pass 17 reuses the Pass-16 explanation builder, existing guarded read-only session, existing deterministic JSON serializer and existing GET-only WSGI adapter. No duplicate explanation model, persistence layer, cache, schema or transport framework is introduced.
