# Pass 15 — Structured Revision Comparison

## Goal

Extend the durable revision-comparison surface from compact counts/material/state into a structured factual side-by-side snapshot, using only facts already committed in the Chat-5 lifecycle store.

## Baseline

```text
main @ 99d8c6d9322f3669a43226e4fd2675fe683ab9f6
branch: chat-5/pass-15
```

Round 14 was closed before this pass started. No previous worker branch was used as implementation baseline.

## Delivered model

`compare_revision_details(left_revision_id, right_revision_id)` returns `RevisionComparisonDetailsResult` with two `RevisionComparisonSnapshot` values.

Each snapshot contains:

- revision code/time/parent/origin/notes/source CAD artifact;
- persisted CAD verification/runtime fields when available;
- complete ordered manufacturing facts already stored by Chat 5;
- complete ordered test facts with exact test artifact IDs;
- complete ordered failure facts with exact evidence IDs and stored cause/feature fields;
- deterministic revision-level lifecycle state.

The result also exposes `changed_categories` in stable order. Categories indicate only that stored structures differ.

## Non-inference boundary

Pass 15 does not:

- score or rank revisions;
- recommend a preferred revision;
- infer causal relationships from failures/tests;
- derive geometry from notes, artifact IDs or failure locations.

The role baseline allows known geometry only when it arrives through an approved upstream contract. No such durable geometry payload exists in the current Chat-5 relational model, so geometry is omitted rather than guessed.

## Read consistency

Detailed comparison runs through the existing guarded read-only connection. Every SQL execute/fetch is checked against the accepted snapshot generation. If a writer advances the authoritative generation during comparison, the old session fails closed with the existing stale-session semantics.

## HTTP exposure

Added additive GET route:

```text
/v1/knowledge/revision-comparison-details
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

It uses the same fresh `SQLiteLifecycleReadOnlySession`, dataclass JSON serialization and request-error mapping as the other knowledge endpoints.

The existing compact endpoint remains unchanged.

## Compatibility

No changes to:

- `core/contracts/**`;
- canonical fixtures;
- SQLite relational schema version (`4`);
- lifecycle snapshot schema;
- cursor formats;
- Chat 1–4 code;
- workflows.

`LIFECYCLE_HTTP_API_SCHEMA_VERSION` stays `mrea.lifecycle-http.v1` because the new route is additive and existing payloads are unchanged.

## Verification

Implementation state independently exercised before documentation:

```text
SHA: a0372ac3e7e4036a1b17d600cc3c29b3d09bb5a4
MREA CI: 36816060128 — SUCCESS
Chat 5 / Lifecycle: 82 passed in 3.54s
Contracts / canonical fixtures: SUCCESS
Chat 4 / Generic CAD gate: SUCCESS
Integration / Chat 4 -> Chat 5: SUCCESS
```

The new detail tests cover exact manufacturing/test/failure evidence, deterministic changed categories, invalid inputs, HTTP serialization and the no-fabricated-geometry boundary.
