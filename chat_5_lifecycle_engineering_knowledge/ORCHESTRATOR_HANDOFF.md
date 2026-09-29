# ORCHESTRATOR HANDOFF — Chat 5 / Pass 5

**Authorization:** direct user instruction to continue development  
**Orchestrator status at branch start:** no newer Chat-5-specific directive was present on `main`; `ORCHESTRATOR_DIRECTIVE.md` there still reported `OD-2026-09-29-003`  
**Branch:** `chat-5/pass-5`  
**Base SHA:** `81a3c1c63e03fbabbd0da1c8191c5ca7ea13cb01` — frozen Chat 5 Pass 4 handoff  
**Independently tested pre-handoff SHA:** `454246c11f069f1f0bfd4565ddd83873deb39d1f`  
**CI run:** `36637716284`  
**Status at handoff:** required Chat 5 gates GREEN

> This handoff is the final worker commit and freezes `chat-5/pass-5`. A Git commit cannot contain its own final SHA. Chat 6 should use the current branch head as the final handoff commit and the tested SHA above as the exact pre-handoff implementation/documentation state independently exercised by CI.

## 1. Delivered functionality

Pass 5 adds a normalized, queryable SQLite lifecycle read model without replacing the already verified Pass 4 authoritative snapshot writer.

Implemented persistence path:

```text
LifecycleUnitOfWork
→ authoritative lifecycle aggregate
→ versioned lifecycle_store snapshot
→ normalized relational projection
→ lifecycle_read_model_meta.snapshot_version
→ same SQLite COMMIT
```

The relational projection is reconstructible and is not a second independent source of truth.

## 2. SQLite migration framework

Added internal migration infrastructure:

- `SQLiteSchemaMigration`;
- `SQLiteSchemaManager`;
- ordered `SQLITE_MIGRATIONS`;
- `lifecycle_schema_migrations` journal;
- relational schema version `2`.

The migration is idempotent on reopen.

No third-party migration package or ORM was introduced.

## 3. Pass 4 database compatibility

Pass 5 preserves the Pass 4 snapshot format:

```text
mrea.lifecycle-snapshot.v1
```

A Pass-4-format database is opened as follows:

```text
preserve lifecycle_store
→ apply missing relational schema migration
→ load authoritative snapshot with existing decoder
→ compare snapshot version with relational projection version
→ backfill normalized tables when versions differ
```

The migration does not increment or rewrite the lifecycle snapshot merely because relational schema was added.

A manually constructed Pass 4 database with snapshot version `4` was verified to migrate to relational schema version `2` while retaining snapshot version `4` and schema `mrea.lifecycle-snapshot.v1`.

## 4. Normalized relational read model

Added normalized tables:

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

Indexes support common lifecycle access paths:

- revision history by part;
- CAD verification status;
- manufacturing by revision;
- physical instances by part/revision/manufacturing record;
- installation by equipment/position;
- tests/failures by revision or physical instance;
- canonical timeline by revision;
- physical timeline and equipment occupancy.

The schema deliberately preserves existing domain behavior: multiple `PhysicalPartInstance` identities may reference one manufacturing record.

## 5. Atomic snapshot + relational projection

A durable Pass 5 writer transaction now performs:

```text
BEGIN IMMEDIATE
→ stale-writer version check
→ update authoritative snapshot
→ rebuild normalized relational projection
→ update relational snapshot_version
→ COMMIT
```

If normalized projection generation fails, the outer Unit of Work rolls back:

- the lifecycle snapshot update;
- all normalized-table mutations;
- read-model version metadata;
- in-memory aggregate mutations.

A successful commit therefore cannot expose a new authoritative snapshot with an older committed relational projection.

## 6. Read-model versioning and self-repair

`lifecycle_read_model_meta.snapshot_version` identifies the authoritative snapshot represented by normalized SQL rows.

On database open:

```text
read_model_version == snapshot version
→ no rebuild

read_model_version != snapshot version
→ deterministic rebuild from authoritative snapshot
```

A stale/deliberately damaged projection was independently tested to self-repair on reopen.

## 7. SQL-native query API

Added `SQLiteLifecycleQueryRepository`, exposed as:

```python
store.queries
```

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

Returns `FailureQueryResult` and includes installation-derived equipment/position context when available.

### Equipment occupancy

```python
store.queries.equipment_occupancy(
    equipment_id=...,
    position=...,
)
```

SQL derives the latest physical event for each instance and retains occupancy only for:

```text
INSTALLED
TESTED
ACTIVATED -> ACTIVE
FAILED
```

A FAILED physical item continues to occupy the position until explicit `REMOVED`, preserving the existing Pass 3 lifecycle semantics.

### Physical timeline

```python
store.queries.physical_timeline(instance_id)
```

Returns normalized physical events ordered by explicit physical-event sequence.

## 8. Canonical contract compatibility

No shared MREA contract or canonical fixture was modified.

Canonical `mrea.lifecycle-event.v1` remains limited to:

```text
REVISION_CREATED
MANUFACTURED
INSTALLED
TESTED
FAILED
```

Migration metadata, relational tables and physical-only states remain Chat-5-internal.

Existing CAD manufacturing eligibility remains unchanged:

```text
CAD_TRANSFER + VERIFIED → manufacturing eligible
CAD_TRANSFER + FAILED   → manufacturing blocked
```

## 9. Files changed in Pass 5

Modified before handoff:

- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `src/mrea_lifecycle/__init__.py`;
- `src/mrea_lifecycle/persistence.py`.

Added:

- `docs/PASS_5_RELATIONAL_READ_MODEL.md`;
- `src/mrea_lifecycle/relational.py`;
- `src/mrea_lifecycle/sqlite_schema.py`;
- `tests/test_relational_persistence.py`.

Final freeze commit modifies only:

- `ORCHESTRATOR_HANDOFF.md`.

No Pass 5 file outside `chat_5_lifecycle_engineering_knowledge/` was modified by Chat 5.

## 10. New deterministic tests

`tests/test_relational_persistence.py` covers:

1. migration from a manually constructed Pass-4-format database;
2. snapshot version and snapshot schema preserved during relational migration;
3. normalized backfill from existing snapshot;
4. migration idempotence on reopen;
5. SQL-native revision history;
6. SQL-native physical timeline;
7. ACTIVE equipment occupancy;
8. failure history with equipment/position context;
9. FAILED instance remains occupying;
10. REMOVED releases occupancy;
11. snapshot version and read-model version remain equal after successful commits;
12. forced read-model writer failure rolls snapshot and relational changes back together;
13. stale/damaged relational projection self-repairs on reopen;
14. multiple physical instances may reference one manufacturing record.

All previous Chat 5 tests remain in the same suite.

## 11. Independent CI evidence

Workflow:

```text
MREA CI / 36637716284
head: 454246c11f069f1f0bfd4565ddd83873deb39d1f
```

### Chat 5 / Lifecycle

Exact result:

```text
25 passed in 0.57s
```

Result: **SUCCESS**.

### Contracts / canonical fixtures

Result: **SUCCESS**.

### Chat 4 / Generic CAD gate

Result: **SUCCESS**.

### Integration / Chat 4 -> Chat 5

Exact result:

```text
2 passed, 1 warning in 0.46s
```

Result: **SUCCESS**.

The warning is the pre-existing Chat 4 `TestDoubleCadAdapter` pytest collection warning and is outside Chat 5 ownership.

No required Chat 5 gate is red at handoff time.

## 12. Build / Reuse decision

Reused:

- Python stdlib `sqlite3` and `json`;
- Pass 4 snapshot format and serializer/deserializer;
- Pass 4 `LifecycleUnitOfWork`;
- Pass 4 optimistic stale-writer guard;
- existing revision/CAD/manufacturing/physical lifecycle models and services.

Not introduced:

- ORM;
- external migration framework;
- external database driver;
- REST framework;
- AI conclusions;
- shared contract changes.

## 13. Known limitations

Still intentionally open:

- incremental relational projection updates instead of full deterministic rebuild after each successful write transaction;
- richer repository-native engineering knowledge queries;
- dedicated read-only connection/process strategy;
- backup/restore tooling;
- REST/API boundary;
- field-device synchronization;
- AI / semantic failure analysis.

The full read-model rebuild is correctness-first and keeps a single authoritative write image. It can later be optimized without changing lifecycle contracts.

## 14. Open Change Requests

None.

Pass 5 required no shared-contract change.

## 15. Ownership verification

Pre-handoff diff against frozen Pass 4 base `81a3c1c63e03fbabbd0da1c8191c5ca7ea13cb01` contained exactly eight files, all under Chat 5 ownership.

This handoff adds only the ninth changed file, `ORCHESTRATOR_HANDOFF.md`.

No Pass 5 changes were made to:

- `core/contracts/`;
- canonical fixtures;
- `.github/workflows/`;
- `tests/integration/`;
- Chat 1-4;
- Chat 6 files.

## 16. Requested acceptance gate

Please verify:

1. Pass-4-format databases migrate/backfill without rewriting authoritative snapshot version;
2. normalized relational data is a reconstructible projection rather than an independent truth source;
3. snapshot and relational projection commit atomically;
4. read-model version follows authoritative snapshot version;
5. stale/damaged relational projection repairs from the snapshot on reopen;
6. SQL revision/failure/equipment/timeline queries preserve existing lifecycle semantics;
7. multiple physical instances per manufacturing record remain valid;
8. canonical `LifecycleEvent v1` remains unchanged;
9. CAD verification manufacturing gate remains intact;
10. required CI gates are green;
11. ownership boundaries are preserved;
12. Chat 6 reconciles the direct-user Pass-5 branch base during central integration because `main` had not yet incorporated the frozen Pass 4 worker state when this pass started.

Requested verdict: **Pass 5 ACCEPTED, ACCEPTED_WITH_REBASE/INTEGRATION FOLLOWUP, or explicit FIX_REQUIRED.**
