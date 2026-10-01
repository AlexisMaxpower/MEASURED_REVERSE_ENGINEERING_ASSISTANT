# Pass 5 — Normalized SQLite Read Model, Migrations & Native Queries

## Authorization and base

Pass 5 was started by direct user instruction after Pass 4 was frozen.

At start time the repository `main` branch still exposed Chat 5 directive `OD-2026-09-29-003`; no newer Chat-5-specific directive had been published there. To preserve the accepted worker state, this pass starts from the exact frozen Pass 4 head:

```text
81a3c1c63e03fbabbd0da1c8191c5ca7ea13cb01
```

No shared contract, canonical fixture, CI workflow, integration test, or other chat-owned file is modified.

## Goal

Build the next persistence layer without replacing the already verified Pass 4 transaction model:

```text
Authoritative lifecycle aggregate
→ versioned snapshot write
→ normalized relational projection
→ same SQLite transaction
→ SQL-native lifecycle queries
```

The snapshot remains the authoritative write image in Pass 5. The normalized SQL tables are a deterministic query projection of that same committed state.

## Why the snapshot remains authoritative

Pass 4 already established:

- atomic canonical + physical writes;
- rollback behavior;
- stale-writer protection;
- durable reopen semantics.

Replacing that mechanism and the persistence schema in one step would combine two risks. Pass 5 instead keeps the proven writer path and adds a normalized relational read model transactionally.

This means the system gains database-native queryability without creating a second independent source of truth.

## Schema migration framework

Added `SQLiteSchemaManager` and ordered `SQLiteSchemaMigration` definitions.

Current relational schema version:

```text
2
```

Migration journal:

```text
lifecycle_schema_migrations
- version
- name
```

The Pass 5 migration creates the normalized lifecycle read model and query indexes. Reopening a migrated database is idempotent; the migration journal prevents duplicate migration application.

## Backward compatibility with Pass 4 databases

A Pass 4 database contains:

```text
lifecycle_store
- schema_version = mrea.lifecycle-snapshot.v1
- version
- payload
```

On first Pass 5 open:

1. the legacy snapshot table is preserved;
2. the relational schema migration is applied;
3. the snapshot is loaded through the existing Pass 4 decoder;
4. normalized tables are backfilled from the loaded aggregate;
5. `lifecycle_read_model_meta.snapshot_version` is set to the authoritative snapshot version.

The snapshot version is not rewritten merely because the relational schema was added.

## Normalized tables

Pass 5 adds:

- `lifecycle_revisions`;
- `lifecycle_cad_artifacts`;
- `lifecycle_manufacturing`;
- `lifecycle_physical_instances`;
- `lifecycle_installations`;
- `lifecycle_tests`;
- `lifecycle_test_artifacts`;
- `lifecycle_failures`;
- `lifecycle_failure_evidence`;
- `lifecycle_events_relational`;
- `lifecycle_physical_events_relational`;
- `lifecycle_read_model_meta`;
- `lifecycle_schema_migrations`.

Indexes are provided for common lifecycle access paths including:

- part revision history;
- CAD verification lookup;
- manufacturing by revision;
- physical instances by part/revision/manufacturing record;
- installation by equipment/position;
- test/failure history by revision or instance;
- canonical timeline by revision;
- physical timeline and equipment occupancy.

## Domain semantics preserved

The relational schema deliberately does not invent a one-instance-per-manufacturing-record rule.

One manufacturing record may be associated with multiple `PhysicalPartInstance` identities, matching the existing domain implementation and allowing batch/manufacturing-record scenarios.

Existing physical rules remain application/domain rules:

- explicit PASSED test before ACTIVE;
- equipment/position occupancy protection;
- failure remains occupying until REMOVED;
- removal/replacement/supersession semantics;
- CAD verification manufacturing eligibility.

## Atomic projection update

Every successful durable Unit of Work now performs:

```text
BEGIN IMMEDIATE
→ validate stale-writer version
→ update authoritative lifecycle snapshot
→ rebuild normalized relational projection
→ set read-model snapshot_version
→ COMMIT
```

If relational projection generation fails, the outer transaction rolls back:

- the snapshot update;
- normalized table changes;
- read-model version metadata;
- in-memory aggregate mutations.

There is no state in which a successful Pass 5 commit exposes a new snapshot with an old relational projection.

## Projection version and self-repair

`lifecycle_read_model_meta` stores the snapshot version represented by the relational projection.

On database open:

```text
snapshot version == read model version
→ no rebuild

snapshot version != read model version
→ rebuild normalized projection from authoritative snapshot
```

This also recovers a deliberately damaged/stale read projection while preserving the authoritative snapshot.

## SQL-native query API

`SQLiteLifecycleQueryRepository` provides committed-state queries that execute directly against normalized SQLite tables.

### Revision history

```python
store.queries.revision_history(part_id)
```

Returns deterministic `RevisionQueryResult` values ordered by creation time and revision ID.

### Failure history

```python
store.queries.failure_history(revision_id=...)
store.queries.failure_history(instance_id=...)
```

Returns `FailureQueryResult` including equipment/position context when the failure references an installation.

### Equipment occupancy

```python
store.queries.equipment_occupancy(
    equipment_id=...,
    position=...,
)
```

The query derives the latest physical event per instance and reports only occupying states:

```text
INSTALLED
TESTED
ACTIVE
FAILED
```

A FAILED part remains returned until REMOVED, matching the Pass 3 physical state machine.

### Physical timeline

```python
store.queries.physical_timeline(instance_id)
```

Returns deterministic physical events ordered by explicit event sequence.

## Build / Reuse decision

Reused:

- Pass 4 `SQLiteLifecycleStore` snapshot format;
- Pass 4 Unit of Work and stale-writer guard;
- existing lifecycle/physical domain models;
- Python stdlib `sqlite3` and `json`.

Added only internal Chat 5 persistence/query modules.

Not introduced:

- ORM;
- external database driver;
- external migration library;
- REST framework;
- shared contract changes;
- AI analysis.

## Verification

New `tests/test_relational_persistence.py` covers:

1. opening a manually constructed Pass 4 database;
2. migration without rewriting snapshot version/schema;
3. automatic normalized backfill;
4. migration idempotence on reopen;
5. revision-history SQL query;
6. physical timeline SQL query;
7. ACTIVE equipment occupancy;
8. failure history with installation/equipment context;
9. FAILED occupancy semantics;
10. REMOVED releases occupancy;
11. snapshot/read-model version equality after commits;
12. forced relational writer failure rolls snapshot and projection back together;
13. stale/damaged read model self-repair on reopen;
14. multiple physical instances may share one manufacturing record.

Independent GitHub-hosted Chat 5 suite on implementation SHA `fc1402132092379c94e59332c2d14bfa1e7a367a`:

```text
25 passed in 1.09s
```

Canonical contract checks also passed on that workflow run.

## Remaining persistence work

Still intentionally open:

- incremental relational projection updates instead of full deterministic rebuild per write transaction;
- richer repository-native engineering queries;
- backup/restore tooling;
- explicit read-only connection / process model for deployed services;
- REST/API boundary;
- field synchronization;
- AI / semantic engineering analysis.

The normalized read model is now structurally ready for those later layers without changing shared lifecycle contracts.
