# Pass 6 — Verified Backup / Restore & Read-Only Lifecycle Access

## Authorization and base

Pass 6 was started by direct user instruction after Pass 5 was frozen.

At branch start, repository `main` still exposed Chat 5 directive `OD-2026-09-29-003`; no newer Chat-5-specific directive was published there. To preserve the complete verified worker state, Pass 6 starts from frozen Pass 5 head:

```text
831460686fe3d506cce68ae2b06fd88ea30ea1bc
```

No shared contract, canonical fixture, CI workflow, integration test, or other chat-owned file is modified.

## Goal

Add an operational recovery/read boundary around the persistence foundation established in Passes 4-5:

```text
committed SQLite lifecycle database
→ consistency validation
→ native SQLite backup snapshot
→ SHA-256 manifest
→ independent verification
→ atomic restore
```

and:

```text
SQLite lifecycle database
→ mode=ro connection
→ query_only=ON
→ synchronized read-model check
→ SQL-native lifecycle queries
```

## Backup format

Backup manifest format:

```text
mrea.lifecycle-backup.v1
```

A manifest records:

- backup creation timestamp in UTC;
- authoritative snapshot schema version;
- authoritative snapshot version;
- relational read-model version;
- relational schema version;
- SHA-256 of the SQLite backup file;
- backup file byte length.

Default sidecar path:

```text
<backup>.manifest.json
```

The backup database itself remains a normal SQLite database. No proprietary container format is introduced.

## Consistency gate before backup

`inspect_lifecycle_database()` opens the source database read-only and requires:

1. `PRAGMA integrity_check` returns `ok`;
2. `PRAGMA foreign_key_check` returns no violations;
3. snapshot schema is the supported `mrea.lifecycle-snapshot.v1`;
4. relational schema version is the current Chat 5 schema version;
5. authoritative snapshot version equals relational read-model snapshot version.

If the relational projection is stale, backup creation fails closed instead of preserving a knowingly inconsistent database image.

The normal writable `SQLiteLifecycleStore` can repair the projection from the authoritative snapshot; backup may then be retried.

## Consistent SQLite copy

Backups use Python stdlib `sqlite3.Connection.backup()` from a `mode=ro` source connection.

This avoids unsafe file-copy behavior while a SQLite database may be active and asks SQLite itself for a transactionally coherent database image.

The copy is first written to a unique temporary file. Before publication it is inspected again and its metadata must equal the source inspection captured for the operation.

The final database and manifest are then published with `os.replace()`.

## Verification

`LifecycleBackupManager.verify_backup()` checks, in order:

1. manifest is readable and uses `mrea.lifecycle-backup.v1`;
2. backup byte size equals manifest;
3. backup SHA-256 equals manifest;
4. SQLite integrity and foreign keys are valid;
5. snapshot/read-model versions are synchronized;
6. backup database versions/schema metadata equal the manifest.

A modified backup or manifest is therefore rejected before restore.

## Restore

`LifecycleBackupManager.restore_backup()` first performs full backup verification.

Restore path:

```text
verified backup
→ SQLite native backup into unique temp destination
→ inspect restored temp database
→ require metadata == verified backup metadata
→ os.replace(temp, final destination)
```

Existing restore destinations are rejected unless `overwrite=True` is explicit.

This prevents accidental destruction of an existing lifecycle database.

## Read-only query session

`SQLiteLifecycleReadOnlySession` provides a dedicated reader path.

Connection mode:

```text
SQLite URI mode=ro
PRAGMA query_only = ON
PRAGMA foreign_keys = ON
```

The session validates:

- snapshot schema version;
- relational schema version;
- snapshot version == relational read-model version.

A stale projection raises `LifecycleReadOnlyStaleError`; the session does not silently repair data because a read-only process must not mutate the database.

Query surface is the existing SQL-native repository:

```python
with SQLiteLifecycleReadOnlySession("lifecycle.db") as session:
    session.queries.revision_history("PART-0042")
    session.queries.failure_history(instance_id="PI-001")
    session.queries.equipment_occupancy(equipment_id="RACK-01")
    session.queries.physical_timeline("PI-001")
```

`refresh()` closes and reopens the read-only connection and returns the newly observed snapshot version.

## Build / Reuse decision

Reused:

- Python stdlib `sqlite3` backup API;
- Python stdlib `hashlib`, `json`, `os`, `pathlib`;
- Pass 4 authoritative snapshot/versioning;
- Pass 5 relational schema version;
- Pass 5 `SQLiteLifecycleQueryRepository`.

Not introduced:

- external backup utility;
- ORM;
- external database driver;
- archive/encryption library;
- REST framework;
- shared contract change;
- AI analysis.

## Deterministic tests

`tests/test_backup_readonly.py` covers:

1. backup creation from a committed lifecycle database;
2. manifest versions, UTC timestamp, SHA-256 and file size;
3. verification of the produced backup;
4. source mutation after backup does not change backup contents;
5. restore reconstructs the exact backed-up lifecycle version;
6. tampered backup bytes are rejected before restore;
7. tampered manifest SHA is rejected;
8. restore refuses overwrite unless explicitly enabled;
9. stale relational projection blocks backup;
10. normal writable store repairs the projection and backup can then succeed;
11. read-only session serves SQL-native queries;
12. SQLite rejects writes through the read-only connection;
13. closed read-only session rejects query access;
14. fresh read-only session observes later committed writer state;
15. stale relational projection blocks read-only access until repaired.

## Intentionally still open

- encrypted/off-host backup transport;
- retention/rotation policy;
- scheduled backup orchestration;
- incremental relational projection updates;
- richer engineering knowledge query catalogue;
- REST/API;
- field-device synchronization;
- AI / semantic failure analysis.

Backup scheduling and retention belong to a later orchestration/deployment layer; this pass establishes the deterministic local primitive first.
