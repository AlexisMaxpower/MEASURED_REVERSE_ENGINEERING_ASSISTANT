# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-01**
- Branch: `chat-5/pass-15`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 15**
- Central baseline: `main` @ `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`
- Tested implementation SHA: `a0372ac3e7e4036a1b17d600cc3c29b3d09bb5a4`
- MREA CI: `36816060128` — **SUCCESS**
- Chat 5: **82 passed in 3.54s**
- State: **Pass 15 implementation verified; final freeze pending**

## Baseline discipline

Pass 15 starts directly from the current shared `main`, not from the previous worker branch. All changes remain under `chat_5_lifecycle_engineering_knowledge/`.

## Gap closed

Pass 14 made revision comparison durable but intentionally compact. Pass 15 adds a richer factual side-by-side view required by the Chat-5 role baseline while keeping the compact API unchanged.

## Structured comparison

`RevisionComparisonSnapshot` exposes committed facts for one revision:

- revision metadata/provenance;
- persisted CAD verification/runtime fields when present;
- ordered manufacturing records;
- ordered tests plus exact artifact IDs;
- ordered failures plus exact evidence IDs and stored cause/feature fields;
- deterministic revision-level lifecycle state.

`RevisionComparisonDetailsResult` contains `left`, `right` and deterministic `changed_categories` for revision metadata, CAD truth, materials, manufacturing methods/records, tests, failures and lifecycle state.

These categories only state that factual structures differ. They do not rank revisions, recommend one, or infer why an outcome occurred.

## Geometry boundary

No geometry delta is emitted. The current committed Chat-5 relational model has no approved upstream geometry-comparison payload. Pass 15 therefore omits geometry instead of fabricating it from notes, failure locations or CAD artifact IDs.

## Snapshot / HTTP behavior

All detail reads use the existing snapshot guard; generation drift fails closed. Added additive GET route:

```text
/v1/knowledge/revision-comparison-details?left_revision_id=...&right_revision_id=...
```

Missing revisions, cross-part comparisons and unexpected query parameters map to existing `400 invalid_request` behavior.

Compatibility is preserved:

- `compare_revisions()` unchanged;
- HTTP schema remains `mrea.lifecycle-http.v1`;
- SQLite relational schema remains version `4`;
- no migration or shared-contract/canonical-fixture change;
- no Chat 1–4/workflow change.

## Regression coverage

`tests/test_revision_comparison_details.py` covers exact metadata, manufacturing facts, test artifacts, failure evidence, lifecycle states, changed categories, fail-closed invalid inputs, GET serialization and absence of fabricated geometry.

Revision-comparison test imports were also cleaned so the Chat-5 suite completes without pytest collection warnings.

## Verification

```text
MREA CI / 36816060128 — SUCCESS
Chat 5 / Lifecycle — 82 passed in 3.54s
Contracts / canonical fixtures — SUCCESS
Chat 4 / Generic CAD gate — SUCCESS
Integration / Chat 4 -> Chat 5 — SUCCESS
```

## Remaining intentional limitations

- geometry comparison until an approved upstream durable fact source exists;
- revision ranking/recommendation;
- semantic/AI interpretation;
- external client authn/authz and deployment edge policy;
- field-device synchronization.

## Freeze rule

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation for Pass 15. After that commit the branch is frozen; final CI is verified on that exact HEAD without another mutation.
