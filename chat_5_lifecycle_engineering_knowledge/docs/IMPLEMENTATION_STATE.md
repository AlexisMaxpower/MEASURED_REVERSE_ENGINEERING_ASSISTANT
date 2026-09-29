# Chat 5 — Implementation State

## Snapshot

- Date: **2026-09-30**
- Branch: `chat-5/pass-6`
- Slice: **Lifecycle & Engineering Knowledge**
- SSOT: **MREA v0.1 + orchestration addendum v0.2**
- Pass 6 authorization: **direct user instruction; no newer Chat-5-specific directive present on `main` at branch start**
- Base SHA: `831460686fe3d506cce68ae2b06fd88ea30ea1bc` (frozen Chat 5 Pass 5)
- State: **verified backup/restore + read-only query access implemented; final handoff pending downstream CI gate**

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
- nested rollback and stale-writer protection;
- normalized relational schema version `2`;
- migration/backfill and read-model self-repair;
- SQL-native revision/failure/equipment/timeline queries.

No shared contract, canonical fixture, CI workflow, integration test, or other chat-owned file was changed.

## Pass 6 additions

### Verified database inspection

Added `inspect_lifecycle_database()`.

It opens the database with SQLite `mode=ro` and validates:

- `PRAGMA integrity_check`;
- `PRAGMA foreign_key_check`;
- snapshot schema version;
- relational schema version;
- authoritative snapshot/read-model version equality.

A structurally damaged or stale-projection database therefore cannot be accepted as a valid backup source.

### Backup manifest

Added `LifecycleBackupManifest` using format:

```text
mrea.lifecycle-backup.v1
```

Manifest fields:

- UTC `created_at`;
- snapshot schema version;
- snapshot version;
- read-model version;
- relational schema version;
- SHA-256;
- byte length.

Default sidecar name:

```text
<backup>.manifest.json
```

### Consistent SQLite backup

`LifecycleBackupManager.create_backup()` uses stdlib `sqlite3.Connection.backup()` from a read-only source connection.

The backup is first written to a unique temporary file, validated, hashed, and only then atomically published with `os.replace()`.

Creation fails closed when:

- source integrity check fails;
- source foreign keys are invalid;
- snapshot/read-model versions differ;
- source/backup metadata differ;
- destination already exists without explicit overwrite;
- backup timestamp is naive.

### Backup verification

`LifecycleBackupManager.verify_backup()` validates:

1. manifest format;
2. byte length;
3. SHA-256;
4. SQLite integrity;
5. foreign keys;
6. lifecycle schema versions;
7. snapshot/read-model synchronization;
8. database metadata against manifest.

A modified backup file or modified manifest is rejected before restore.

### Verified restore

`LifecycleBackupManager.restore_backup()` first performs full backup verification.

Restore then uses SQLite native backup into a unique temporary destination, validates the restored image against the verified backup, and atomically publishes it.

Existing targets are protected unless `overwrite=True` is explicit.

### Read-only lifecycle session

Added `SQLiteLifecycleReadOnlySession`.

Connection guarantees:

```text
SQLite URI mode=ro
PRAGMA query_only = ON
PRAGMA foreign_keys = ON
```

The session exposes the existing `SQLiteLifecycleQueryRepository` as `.queries`.

It rejects:

- unsupported snapshot schema;
- unsupported relational schema;
- missing persistence metadata;
- stale relational projection.

The read-only process does not self-repair the database. A writable `SQLiteLifecycleStore` must perform repair first.

`refresh()` closes/reopens the reader and returns the newly observed snapshot version.

## Build / Reuse

No third-party dependency was added.

Reused:

- Python stdlib `sqlite3` backup API;
- `hashlib`, `json`, `os`, `pathlib`;
- Pass 4 snapshot/versioning model;
- Pass 5 relational schema/version metadata;
- Pass 5 `SQLiteLifecycleQueryRepository`.

Not introduced:

- external backup utility;
- external database driver;
- ORM;
- encryption library;
- REST framework;
- AI layer;
- shared contract amendment.

## Verification

### New tests

`tests/test_backup_readonly.py` verifies:

1. committed database backup creation;
2. backup manifest timestamp/versions/hash/size;
3. backup verification;
4. source mutations after backup do not alter the backup image;
5. restore returns the backed-up version rather than later source state;
6. tampered backup bytes rejected;
7. tampered manifest hash rejected;
8. restore overwrite blocked by default;
9. explicit overwrite works;
10. stale relational projection blocks backup;
11. writable reopen repairs projection and then backup succeeds;
12. read-only SQL-native query access;
13. SQLite write attempts through read-only handle fail;
14. closed read-only session rejects queries;
15. later committed writer state is visible to a fresh reader;
16. stale relational projection blocks read-only session until repaired.

### GitHub-hosted Chat 5 suite

Implementation/documentation SHA:

```text
52ebc6614064c6541c65651a5af58d99bb5e65c4
```

Exact result:

```text
31 passed in 3.73s
```

Status: **SUCCESS**.

### Canonical contracts

Same workflow run:

```text
Contracts / canonical fixtures
```

Status: **SUCCESS**.

### Chat 4 generic gate

Status: **SUCCESS**.

### Cross-slice boundary

`Integration / Chat 4 -> Chat 5` remains the required final downstream gate before handoff freeze.

## Files added in Pass 6

- `src/mrea_lifecycle/backup.py`;
- `src/mrea_lifecycle/read_only.py`;
- `tests/test_backup_readonly.py`;
- `docs/PASS_6_BACKUP_RESTORE_READ_ONLY.md`.

## Files modified in Pass 6

- `src/mrea_lifecycle/__init__.py`;
- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `ORCHESTRATOR_HANDOFF.md` at final freeze.

## Known limitations

Still open:

- encrypted/off-host backup transport;
- retention/rotation policy;
- scheduled backup orchestration;
- incremental relational projection updates;
- richer engineering knowledge query catalogue;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis.

The current backup primitive is local and deterministic by design. Scheduling, remote storage, encryption and retention belong to later deployment/orchestration layers.

## Handoff rule

After `ORCHESTRATOR_HANDOFF.md` is updated, `chat-5/pass-6` is frozen. No later commit is allowed unless Chat 6 explicitly requests a correction.
