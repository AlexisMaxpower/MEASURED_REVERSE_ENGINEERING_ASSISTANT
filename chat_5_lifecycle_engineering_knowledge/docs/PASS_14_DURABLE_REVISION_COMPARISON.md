# Pass 14 — Durable Revision Comparison

## Goal

Close the remaining split between the original in-memory revision comparison projection and the committed SQLite engineering-knowledge/read-only surface.

Pass 14 makes revision comparison available from durable committed facts while preserving the already-defined factual result shape and state projection semantics.

## Baseline

```text
main @ d6758d3a4c5eb2116ac2e48c3a77e65c10688b12
branch: chat-5/pass-14
```

Round 13 was already integrated and closed before this branch was created.

## Existing capability reused

The early projection layer already defined:

```text
RevisionComparisonResult
RevisionComparison.compare(left_revision_id, right_revision_id)
LifecycleStateProjection
```

That behavior was not replaced. Pass 14 reuses `RevisionComparisonResult` and reproduces its deterministic factual semantics from the normalized committed read model.

## Durable API

`SQLiteLifecycleReadOnlySession.knowledge` now exposes:

```python
compare_revisions(left_revision_id, right_revision_id)
```

Result fields:

```text
left_revision_id
right_revision_id
left_materials
right_materials
left_failure_count
right_failure_count
left_test_count
right_test_count
left_state
right_state
```

Materials are distinct and sorted. Counts come from exact persisted failure/test records.

## Revision-level state semantics

The durable comparison intentionally retains the historical revision projection semantics.

For one revision:

1. collect committed canonical lifecycle events;
2. order deterministically by `(occurred_at, sequence)`;
3. if the latest `FAILED` event is later than the latest `INSTALLED` event, project `FAILED`;
4. otherwise use the latest canonical event mapping:
   - `REVISION_CREATED -> DRAFT`;
   - `MANUFACTURED -> MANUFACTURED`;
   - `INSTALLED -> ACTIVE`;
   - `TESTED -> ACTIVE`;
   - `FAILED -> FAILED`.

Therefore historical failures remain counted even if a later installation/test returns the revision-level projection to ACTIVE. Pass 14 does not reinterpret this behavior.

## Integrity constraints

Comparison is allowed only when:

```text
left revision exists
AND right revision exists
AND left.part_id == right.part_id
```

Otherwise it fails closed with `ValueError`.

A committed revision with no valid lifecycle event projection is treated as read-model integrity failure, not silently assigned a guessed state.

## Snapshot safety

The comparison is executed through the existing Pass-13 `_SnapshotGuardedConnection`.

The operation performs several SQL statements, but each statement is checked against the generation accepted at session open:

```text
before SQL execute
→ authoritative/read-model/schema metadata check
→ SQL read/fetch
→ metadata check after fetch
```

If a writer commits after one comparison statement but before another, the next guard detects drift and raises `LifecycleReadOnlyStaleError`. No mixed old/new generation result is returned.

Explicit `session.refresh()` closes the old handle and accepts the next committed generation.

## HTTP read boundary

Added:

```text
GET /v1/knowledge/revision-comparison
    ?left_revision_id=<revision-id>
    &right_revision_id=<revision-id>
```

Success uses the standard read-only envelope:

```json
{
  "schema_version": "mrea.lifecycle-http.v1",
  "snapshot_version": 1,
  "data": {
    "left_revision_id": "R1",
    "right_revision_id": "R2"
  }
}
```

The full `data` object contains all `RevisionComparisonResult` fields.

Existing HTTP error handling maps invalid parameters and invalid comparison inputs to:

```text
400 invalid_request
```

This is an additive route. Existing routes/payloads and `mrea.lifecycle-http.v1` are unchanged.

## Out of scope

Pass 14 deliberately does not add:

- revision ranking;
- a better/worse verdict;
- recommendation of a preferred revision;
- inferred causal links between material/test/failure differences;
- semantic or AI analysis;
- a new shared contract;
- a new persistence table/materialized view;
- a new cursor format.

Those would be new product semantics rather than durable exposure of an already-defined factual projection.

## Verification

Implementation + HTTP tested at:

```text
8f5394c9ad2ffe1bfefc02021b78a9c7a17320d0
```

GitHub Actions:

```text
MREA CI / 36811581113 — SUCCESS
```

Required gates:

```text
Chat 5 / Lifecycle                 SUCCESS
Contracts / canonical fixtures     SUCCESS
Chat 4 / Generic CAD gate          SUCCESS
Integration / Chat 4 -> Chat 5    SUCCESS
```

## Ownership

All Pass-14 mutations are under:

```text
chat_5_lifecycle_engineering_knowledge/
```

No shared contract, workflow, root integration test or Chat 1–4 source mutation is required.
