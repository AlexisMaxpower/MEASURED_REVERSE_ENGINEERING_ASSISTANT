# Pass 12 — Materialized Analytical Aggregates

## Goal

Reduce repeated SQL aggregation cost for factual lifecycle knowledge while preserving the exact already-tested semantics and snapshot/cursor guarantees from Passes 7–11.

Pass 12 intentionally does **not** add predictive/semantic analytics. It materializes only existing deterministic queries.

## Materialized surfaces

### Revision outcomes

Table:

```text
lifecycle_revision_outcomes_materialized
```

Identity/order:

```text
revision_id PRIMARY KEY
part_id
created_at ASC
revision_id ASC
```

Stored factual counts:

- manufacturing records;
- physical instances;
- activated/failed/removed/superseded instances;
- failure records.

### Failure patterns

Table:

```text
lifecycle_failure_patterns_materialized
```

The same grouping dimensions as the existing raw query are retained:

```text
failure_type
damage_location
confirmed_cause
```

The same deterministic order from Pass 11 is retained:

```text
occurrence_count DESC
failure_type ASC
damage_location ASC
cause_null_rank ASC
cause_sort ASC
```

Precomputed scopes:

```text
GLOBAL
PART
REVISION
```

This allows the existing public filters to select a pre-grouped factual set without recomputing `COUNT`, `COUNT(DISTINCT)`, `MIN` and `MAX` for each read.

## Consistency model

The authoritative source remains `lifecycle_store` plus the normalized relational projection. Materialized tables are derived read-model data only.

Refresh is bound to publication of `lifecycle_read_model_meta.snapshot_version` and occurs in the same SQLite transaction as the normalized read-model replacement.

Therefore the visibility rule remains:

```text
committed authoritative snapshot version
== normalized read-model version
== materialized aggregate generation
```

A v3 database migrating to v4 has its read-model meta version invalidated. Store open then runs the existing deterministic projection repair path and publishes a current v4 projection before normal read-only service.

## Read path

`SQLiteLifecycleReadOnlySession` instantiates:

```text
SQLiteMaterializedEngineeringKnowledgeRepository
```

It subclasses the Pass-10.1/11 keyset repository.

Materialized direct/v2 methods:

```text
revision_outcomes
revision_outcomes_page
failure_patterns
failure_patterns_page
```

All other methods are inherited unchanged.

## Cursor compatibility

### v2

New/v2 revision and failure pages read materialized rows with the existing continuation keys and `LIMIT + 1`. OFFSET is not used.

### v1

If a valid legacy `mrea.knowledge-cursor.v1` is supplied, execution delegates to the historical raw OFFSET implementation.

This preserves already-issued cursor semantics instead of translating offsets into a newly materialized ordering implicitly.

## Failure behavior

Unchanged fail-closed behavior remains in force for:

- malformed cursors;
- query fingerprint mismatch;
- snapshot version mismatch;
- invalid keyset shape;
- unsupported relational schema version;
- stale read-model version.

## Verification

Tested implementation:

```text
0e4b2df0b144fe7116b7e94141be85266a0820fc
MREA CI 36802306777 — SUCCESS
Chat 5: 72 passed in 11.64s
```

The test suite compares materialized results against the former raw repository on the same committed database and verifies atomic refresh after a later write transaction.
