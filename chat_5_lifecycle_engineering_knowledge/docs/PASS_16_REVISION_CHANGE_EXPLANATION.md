# Pass 16 — Evidence-Backed Revision Change Explanation

## Goal

Advance the Chat-5 Engineering Knowledge layer from Pass-15 structured side-by-side comparison to a deterministic explanation surface that identifies exactly which committed facts changed and which stored records/artifacts support each side of the delta.

This is the first explicit `revision explanations` step from the MREA Engineering Knowledge roadmap, implemented without semantic/AI inference.

## Repository baseline

At worker start, shared `main` remained at Round-14 closure:

```text
main: 99d8c6d9322f3669a43226e4fd2675fe683ab9f6
```

Chat-5 Pass 15 was already published and frozen at:

```text
chat-5/pass-15: 70ac1fa5331df47525e42ad4f2d848abddb268fe
```

Because Pass 15 had not yet been integrated to `main`, Pass 16 was branched from the frozen Chat-5 Pass-15 head to preserve the already-published structured comparison dependency. No unrelated slice was copied or modified.

## Delivered capability

`mrea_lifecycle.revision_explanation` adds:

- `RevisionChangeSource` — revision ID plus exact supporting record/artifact IDs;
- `RevisionChangeFact` — one deterministic left-to-right field/category difference;
- `RevisionChangeExplanation` — ordered factual explanation for the compared pair;
- `build_revision_change_explanation(details)` — pure transformation over Pass-15 durable comparison details;
- `explain_revision_changes(knowledge, left_revision_id, right_revision_id)` — convenience read surface that delegates durable reads to `compare_revision_details(...)`.

## Factual coverage

The explanation emits only changed facts, in stable category/field order, for:

- revision metadata;
- persisted CAD verification/runtime truth;
- materials;
- manufacturing methods;
- complete manufacturing records;
- tests and exact test artifact IDs;
- failures and exact failure evidence artifact IDs;
- deterministic lifecycle state.

For categories backed by manufacturing/tests/failures, each side includes the exact persisted record IDs and artifact IDs available in the Chat-5 snapshot.

## Fail-closed consistency

The explanation is derived from the existing snapshot-guarded `compare_revision_details(...)` result rather than running a second independent read path.

`build_revision_change_explanation(...)` verifies that the ordered categories represented by emitted facts exactly equal the durable comparison's `changed_categories`. A mismatch raises `LifecycleKnowledgeIntegrityError` instead of silently returning a partial or contradictory explanation.

Missing revisions and cross-part comparisons preserve the existing fail-closed `ValueError` behavior from Pass 15.

## Non-inference boundary

Pass 16 does not:

- rank revisions;
- recommend a preferred revision;
- claim that a change caused a test/failure outcome;
- convert estimated causes into confirmed causes;
- synthesize geometry;
- infer geometry changes from notes, artifact IDs, failure locations or CAD artifact IDs;
- introduce semantic search, embeddings or an LLM.

The output is structured evidence for later semantic/AI layers, not an AI conclusion.

## Compatibility

No changes to:

- `core/contracts/**`;
- canonical fixtures;
- SQLite schema version;
- lifecycle snapshot schema;
- cursor formats;
- HTTP API schema or routes;
- Chat 1–4 code;
- workflows.

## Tests

`tests/test_revision_change_explanation.py` covers:

- deterministic category and field ordering;
- exact manufacturing/test/failure source IDs;
- exact test/failure artifact evidence IDs;
- lifecycle-state delta preservation;
- absence of fabricated geometry;
- same-revision zero-delta behavior;
- missing/cross-part fail-closed validation.
