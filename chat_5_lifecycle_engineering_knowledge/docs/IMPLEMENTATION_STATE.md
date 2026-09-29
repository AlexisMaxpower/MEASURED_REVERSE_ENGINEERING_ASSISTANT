# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-30**
- Branch: `chat-5/pass-5`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 5 authorization: **direct user instruction; no newer Chat-5-specific directive present on `main` at branch start**
- Base SHA: `81a3c1c63e03fbabbd0da1c8191c5ca7ea13cb01` (frozen Chat 5 Pass 4)
- State: **normalized relational read model + migration framework + SQL-native queries implemented; handoff pending final CI freeze**

## Preserved baseline

Still active and unchanged:

- Revision / Manufacturing / Installation / Test / Failure domain;
- canonical CADPackage + CADVerificationReport transfer;
- VERIFIED manufacturing eligibility gate;
- canonical `LifecycleEvent v1` adapter;
- physical-instance state machine;
- exact instance/evidence linkage;
- equipment/position occupancy protection;
- removal/replacement/supersession semantics;
- `LifecycleRepository` + `LifecycleUnitOfWork`;
- authoritative `mrea.lifecycle-snapshot.v1` SQLite snapshot;
- nested rollback and stale-writer protection.

No shared contract, canonical fixture, CI workflow, integration test, or other chat-owned file was changed.

## Pass 5 additions

### Relational schema migration framework

Added:

- `SQLiteSchemaMigration`;
- `SQLiteSchemaManager`;
- ordered `SQLITE_MIGRATIONS`;
- migration journal `lifecycle_schema_migrations`;
- relational schema version `2`.

The first migration creates the normalized lifecycle read model and indexes.

Opening an already migrated database is idempotent.

### Backward-compatible Pass 4 migration

Pass 4 database state remains authoritative and is not rewritten simply because Pass 5 introduces normalized tables.

Open path:

```text
ensure legacy lifecycle_store exists
→ apply missing relational migrations
→ load authoritative snapshot
→ compare snapshot version with read-model version
→ backfill normalized tables only when versions differ
```

A manually created Pass-4-format database with snapshot version `4` is verified to open under Pass 5 with:

```text
loaded_version = 4
read_model_version = 4
relational_schema_version = 2
```

The snapshot remains:

```text
schema_version = mrea.lifecycle-snapshot.v1
version = 4
```

### Normalized relational read model

Added tables:

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
- `lifecycle_read_model_meta`.

The schema uses indexes for part, revision, verification status, manufacturing, equipment/position, instance history and event timelines.

The read model preserves existing domain semantics rather than adding new ones. In particular, multiple physical instances may reference the same manufacturing record.

### Atomic projection update

Pass 5 durable commit path:

```text
BEGIN IMMEDIATE
→ stale-writer check
→ update authoritative lifecycle_store snapshot
→ rebuild normalized relational projection
→ set lifecycle_read_model_meta.snapshot_version
→ COMMIT
```

If relational projection generation fails:

- snapshot update rolls back;
- normalized tables roll back;
- read-model version metadata rolls back;
- in-memory Unit-of-Work state rolls back.

### Read-model version and repair

`read_model_version` is explicit and must represent the same committed version as `loaded_version` after a successful commit.

On reopen, a stale or deliberately damaged projection is repaired from the authoritative snapshot whenever:

```text
read_model_version != snapshot version
```

This makes relational data reconstructible rather than an independent source of truth.

### SQL-native query repository

`SQLiteLifecycleQueryRepository` exposes committed-state SQL queries.

#### `revision_history(part_id)`

Returns deterministic `RevisionQueryResult` rows ordered by creation time and revision ID.

#### `failure_history(revision_id=..., instance_id=...)`

Returns deterministic `FailureQueryResult` rows and joins installation context to expose equipment/position where available.

#### `equipment_occupancy(equipment_id=..., position=...)`

Derives the latest physical event per instance directly in SQL.

Occupying event/state semantics:

```text
INSTALLED
TESTED
ACTIVATED -> ACTIVE
FAILED
```

`REMOVED` and `SUPERSEDED` are not occupying.

A failed instance therefore remains visible as equipment occupancy until explicit removal, matching the Pass 3 domain projection.

#### `physical_timeline(instance_id)`

Returns deterministic physical event rows ordered by explicit sequence.

## Build / Reuse

No third-party dependency was added.

Reused:

- Python stdlib `sqlite3`;
- Pass 4 snapshot serializer/deserializer;
- Pass 4 Unit of Work;
- Pass 4 stale-writer guard;
- existing lifecycle and physical domain services.

Not introduced:

- ORM;
- external migration package;
- external DB driver;
- REST framework;
- AI layer;
- shared contract amendment.

## Verification

### New tests

`tests/test_relational_persistence.py` verifies:

1. migration from manually constructed Pass-4-format database;
2. snapshot version/schema preserved during relational migration;
3. normalized backfill;
4. migration idempotence on reopen;
5. SQL-native revision history;
6. SQL-native physical timeline;
7. ACTIVE equipment occupancy;
8. failure history with equipment/position context;
9. FAILED remains occupying;
10. REMOVED releases occupancy;
11. snapshot/read-model version equality;
12. forced read-model failure rolls back snapshot + relational state;
13. reopen repairs stale/damaged projection;
14. multiple physical instances may share one manufacturing record.

### GitHub-hosted Chat 5 suite

Implementation SHA:

```text
fc1402132092379c94e59332c2d14bfa1e7a367a
```

Exact result:

```text
25 passed in 1.09s
```

Status: **SUCCESS**.

### Canonical contracts

Same workflow run:

```text
Contracts / canonical fixtures
```

Status: **SUCCESS**.

### Cross-slice boundary

`Integration / Chat 4 -> Chat 5` remains the required final downstream gate before handoff freeze.

## Files added in Pass 5

- `src/mrea_lifecycle/sqlite_schema.py`;
- `src/mrea_lifecycle/relational.py`;
- `tests/test_relational_persistence.py`;
- `docs/PASS_5_RELATIONAL_READ_MODEL.md`.

## Files modified in Pass 5

- `src/mrea_lifecycle/persistence.py`;
- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Known limitations

Still open:

- incremental read-model updates instead of full deterministic rebuild per successful writer transaction;
- larger engineering knowledge query catalogue;
- dedicated read-only connection/process strategy;
- backup/restore tooling;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis.

The current full projection rebuild is intentionally correctness-first. It keeps a single authoritative write image and allows later optimization without changing lifecycle contracts.

## Handoff rule

After `ORCHESTRATOR_HANDOFF.md` is updated, `chat-5/pass-5` is frozen. No later commit is allowed unless Chat 6 explicitly requests a correction.
