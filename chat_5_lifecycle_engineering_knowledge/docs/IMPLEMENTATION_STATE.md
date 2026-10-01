# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-01**
- Branch: `chat-5/pass-14`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 14**
- Central baseline checked before work: `main` @ `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`
- Central state at start: **Round 13 closed/integrated; next full worker pass ready**
- Tested implementation SHA: `8f5394c9ad2ffe1bfefc02021b78a9c7a17320d0`
- MREA CI: `36811581113` — **SUCCESS**
- State: **Pass 14 implementation verified; documentation published; final freeze pending**

## Baseline discipline

Pass 14 was branched directly from current shared `main`, not from `chat-5/pass-13` worker history. `main` remained at the same baseline through implementation verification.

All changes are under `chat_5_lifecycle_engineering_knowledge/`.

## Gap closed in Pass 14

The product already had `RevisionComparisonResult` and deterministic `RevisionComparison` in the original in-memory projection layer. The durable SQLite knowledge/read-only surface introduced later did not expose equivalent comparison capability.

This created two truths for the same intended factual operation:

```text
in-memory projection → revision comparison available
committed durable read model → revision comparison unavailable
```

Pass 14 closes that gap by reusing the existing result shape and preserving historical projection semantics over committed relational facts.

## Pass 14 architecture

### Durable comparison repository

Added `SQLiteRevisionComparisonEngineeringKnowledgeRepository`, extending the current materialized engineering knowledge repository.

`compare_revisions(left_revision_id, right_revision_id)` reads only committed read-model facts and returns the existing `RevisionComparisonResult`:

- left/right revision IDs;
- distinct sorted manufacturing materials;
- exact failure counts;
- exact test counts;
- revision-level `LifecycleState`.

No ranking, recommendation, score, causal interpretation or AI inference is produced.

### Input integrity

The comparison requires:

1. both revision IDs exist in the committed read model;
2. both revisions share the same `part_id`.

Missing revisions and cross-part comparisons raise `ValueError` and fail closed.

### Preserved state semantics

Pass 14 intentionally preserves the historical `LifecycleStateProjection` behavior rather than inventing a new state definition:

- a failure newer than the latest installation projects `FAILED`;
- a later installation/test can project the revision back to `ACTIVE` while failure history remains counted;
- otherwise the latest canonical revision event maps to `DRAFT`, `MANUFACTURED`, `ACTIVE` or `FAILED` as before.

Event ordering is deterministic by `(occurred_at, sequence)`.

### Snapshot consistency

Comparison uses the Pass-13 `_SnapshotGuardedConnection`.

Because comparison needs multiple SQL statements, every statement is guarded before execute and after fetch. If another writer commits between those statements, the next guard detects generation drift and raises `LifecycleReadOnlyStaleError`; a mixed-generation comparison is not returned.

`SQLiteLifecycleReadOnlySession.refresh()` explicitly accepts the new committed generation.

### HTTP surface

Added additive GET route:

```text
/v1/knowledge/revision-comparison?left_revision_id=...&right_revision_id=...
```

The route opens the same fresh guarded read-only session used by existing knowledge endpoints and serializes the existing dataclass result.

Missing parameters, unexpected parameters, missing revisions and cross-part inputs map through the existing `400 invalid_request` boundary.

`LIFECYCLE_HTTP_API_SCHEMA_VERSION` remains `mrea.lifecycle-http.v1`; existing routes and payloads are unchanged.

### No schema / shared-contract change

- `SQLITE_RELATIONAL_SCHEMA_VERSION` remains `4`;
- no SQLite migration;
- no change to `core/contracts/**`;
- no canonical fixture change;
- no cursor format change;
- no Chat 1–4 change;
- no workflow change.

## Regression coverage

`tests/test_revision_comparison_durable.py` verifies:

1. durable comparison preserves existing material/count/state semantics;
2. failure followed by a later installation/test projects ACTIVE as in the original in-memory implementation;
3. missing revision is rejected;
4. cross-part comparison is rejected;
5. an external writer commit makes the old read-only session fail closed;
6. `refresh()` accepts the new generation and comparison reflects it.

`tests/test_revision_comparison_http.py` verifies:

1. GET comparison serialization and snapshot metadata;
2. required parameters;
3. cross-part rejection;
4. unexpected parameter rejection;
5. existing HTTP schema version is preserved.

## Verification

Tested implementation SHA:

```text
8f5394c9ad2ffe1bfefc02021b78a9c7a17320d0
```

Workflow:

```text
MREA CI / 36811581113 — SUCCESS
```

Required results:

- `Chat 5 / Lifecycle` — **SUCCESS**;
- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 4 / Generic CAD gate` — **SUCCESS**;
- `Integration / Chat 4 -> Chat 5` — **SUCCESS**.

## Shared-contract impact

None.

## Standing SOLIDWORKS host qualification

Unchanged. Standing real-host qualification remains owned by the dedicated workflow authority; Pass 14 neither infers nor mirrors it.

## Remaining intentional limitations

- revision ranking/recommendation;
- semantic/AI interpretation;
- external client authn/authz;
- deployment/TLS/CORS/rate-limit policy;
- field-device synchronization.

## Freeze rule

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation for Pass 14. After that commit, `chat-5/pass-14` is frozen. Final CI must be verified on that exact branch HEAD without a follow-up mutation.
