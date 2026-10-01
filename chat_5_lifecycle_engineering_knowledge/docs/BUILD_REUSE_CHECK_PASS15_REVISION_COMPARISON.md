# Build / Reuse Check — Pass 15 Structured Revision Comparison

## Decision

**Reuse existing durable lifecycle/read-only infrastructure; build only the missing structured comparison projection.**

No new dependency, database table, migration, shared contract or transport framework is required.

## Reused components

- `SQLiteLifecycleReadOnlySession` for read-only lifecycle access;
- `_SnapshotGuardedConnection` for generation consistency;
- existing normalized lifecycle tables for revision/manufacturing/test/failure facts;
- existing test-artifact and failure-evidence link tables;
- existing revision lifecycle-state projection semantics;
- `SQLiteMaterializedEngineeringKnowledgeRepository` inheritance chain;
- existing dataclass JSON serializer and GET-only WSGI boundary;
- existing HTTP v1 invalid-request behavior.

## Built locally

Only the missing factual read projection was added:

- structured immutable dataclasses for manufacturing/test/failure facts;
- one revision snapshot type;
- one left/right detailed comparison result;
- deterministic changed-category calculation;
- additive GET route;
- focused regression tests.

## Why not add schema fields

The required data already exists in normalized Chat-5 tables. Copying it into a new comparison table would create another derived truth and require synchronization/migration work with no product benefit.

## Why geometry is absent

Chat 5 currently has artifact/provenance identifiers but no approved durable geometry-comparison payload. Parsing or inferring dimensions/features locally would cross ownership and violate the factual deterministic boundary. The correct reuse decision is therefore to expose existing facts and leave geometry absent until an approved upstream source exists.

## Why the HTTP schema version is unchanged

The new endpoint is additive. Existing routes, required parameters and response bodies are untouched. The new response is serialized through the current generic factual envelope, so no breaking HTTP contract change is introduced.

## Dependency result

```text
new external dependencies: none
SQLite migration: none
shared contract change: none
canonical fixture change: none
Chat 1–4 mutation: none
workflow mutation: none
```

## Verification basis

```text
implementation SHA: a0372ac3e7e4036a1b17d600cc3c29b3d09bb5a4
MREA CI: 36816060128 — SUCCESS
Chat 5: 82 passed in 3.54s
Chat 4 -> Chat 5 integration: SUCCESS
```
