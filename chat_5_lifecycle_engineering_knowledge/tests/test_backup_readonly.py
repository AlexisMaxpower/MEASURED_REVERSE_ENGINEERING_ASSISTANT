from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from mrea_lifecycle import (
    LIFECYCLE_BACKUP_FORMAT_VERSION,
    LifecycleBackupConsistencyError,
    LifecycleBackupError,
    LifecycleBackupIntegrityError,
    LifecycleBackupManager,
    LifecycleReadOnlyError,
    LifecycleReadOnlyStaleError,
    LifecycleUnitOfWork,
    ManufacturingRecord,
    Revision,
    SQLiteLifecycleReadOnlySession,
    SQLiteLifecycleStore,
)


T0 = datetime(2026, 9, 30, 1, 0, tzinfo=timezone.utc)


def _create_committed_database(path) -> None:
    store = SQLiteLifecycleStore(path)
    uow = LifecycleUnitOfWork(store)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R1",
                part_id="PART-BACKUP",
                revision_code="REV01",
                created_at=T0,
            ),
            event_id="LC-R1",
        )
        uow.manufacturing.record(
            ManufacturingRecord(
                manufacturing_id="M1",
                revision_id="R1",
                material="PETG",
                method="FDM",
                manufactured_at=T0 + timedelta(hours=1),
            ),
            event_id="LC-M1",
        )
    store.close()


def test_backup_restore_roundtrip_preserves_exact_committed_version(tmp_path) -> None:
    database = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    _create_committed_database(database)

    manifest = LifecycleBackupManager.create_backup(
        database,
        backup,
        created_at=T0 + timedelta(hours=2),
    )

    assert manifest.format_version == LIFECYCLE_BACKUP_FORMAT_VERSION
    assert manifest.snapshot_version == 1
    assert manifest.read_model_version == 1
    assert manifest.relational_schema_version == 2
    assert manifest.created_at == "2026-09-30T03:00:00Z"
    assert manifest.size_bytes == backup.stat().st_size
    assert len(manifest.sha256) == 64

    verification = LifecycleBackupManager.verify_backup(backup)
    assert verification.manifest == manifest
    assert verification.inspection.snapshot_version == 1

    source = SQLiteLifecycleStore(database)
    source_uow = LifecycleUnitOfWork(source)
    with source_uow.transaction():
        source_uow.revisions.create(
            Revision(
                revision_id="R2",
                part_id="PART-BACKUP",
                revision_code="REV02",
                created_at=T0 + timedelta(hours=4),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
    assert source.loaded_version == 2
    source.close()

    LifecycleBackupManager.restore_backup(backup, restored)
    restored_store = SQLiteLifecycleStore(restored)
    assert restored_store.loaded_version == 1
    assert set(restored_store.revisions) == {"R1"}
    assert set(restored_store.manufacturing_records) == {"M1"}
    assert [
        item.revision_id
        for item in restored_store.queries.revision_history("PART-BACKUP")
    ] == ["R1"]
    restored_store.close()


def test_tampered_backup_is_rejected_before_restore(tmp_path) -> None:
    database = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    _create_committed_database(database)
    LifecycleBackupManager.create_backup(database, backup, created_at=T0)

    with backup.open("ab") as stream:
        stream.write(b"tamper")

    with pytest.raises(LifecycleBackupIntegrityError, match="size mismatch"):
        LifecycleBackupManager.verify_backup(backup)
    with pytest.raises(LifecycleBackupIntegrityError):
        LifecycleBackupManager.restore_backup(backup, restored)
    assert not restored.exists()


def test_manifest_tamper_and_restore_overwrite_are_fail_closed(tmp_path) -> None:
    database = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    manifest_path = tmp_path / "backup.db.manifest.json"
    restored = tmp_path / "restored.db"
    _create_committed_database(database)
    LifecycleBackupManager.create_backup(database, backup, created_at=T0)

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    original_sha = raw["sha256"]
    raw["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(LifecycleBackupIntegrityError, match="SHA-256 mismatch"):
        LifecycleBackupManager.verify_backup(backup)

    raw["sha256"] = original_sha
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")
    restored.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(LifecycleBackupError, match="already exists"):
        LifecycleBackupManager.restore_backup(backup, restored)
    assert restored.read_text(encoding="utf-8") == "do not overwrite"

    LifecycleBackupManager.restore_backup(backup, restored, overwrite=True)
    restored_store = SQLiteLifecycleStore(restored)
    assert set(restored_store.revisions) == {"R1"}
    restored_store.close()


def test_backup_refuses_stale_relational_projection_until_repaired(tmp_path) -> None:
    database = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    _create_committed_database(database)

    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE lifecycle_read_model_meta SET snapshot_version = 0 WHERE singleton = 1"
    )
    connection.commit()
    connection.close()

    with pytest.raises(
        LifecycleBackupConsistencyError,
        match="snapshot/read-model version mismatch",
    ):
        LifecycleBackupManager.create_backup(database, backup, created_at=T0)
    assert not backup.exists()

    repaired = SQLiteLifecycleStore(database)
    assert repaired.loaded_version == repaired.read_model_version == 1
    repaired.close()

    manifest = LifecycleBackupManager.create_backup(database, backup, created_at=T0)
    assert manifest.snapshot_version == manifest.read_model_version == 1


def test_read_only_session_serves_queries_and_sqlite_rejects_writes(tmp_path) -> None:
    database = tmp_path / "source.db"
    _create_committed_database(database)

    with SQLiteLifecycleReadOnlySession(database) as session:
        assert session.snapshot_version == session.read_model_version == 1
        assert session.relational_schema_version == 2
        history = session.queries.revision_history("PART-BACKUP")
        assert [item.revision_id for item in history] == ["R1"]

        assert session._connection is not None
        with pytest.raises(sqlite3.OperationalError):
            session._connection.execute("DELETE FROM lifecycle_revisions")

    with pytest.raises(LifecycleReadOnlyError, match="closed"):
        _ = session.queries

    writer = SQLiteLifecycleStore(database)
    uow = LifecycleUnitOfWork(writer)
    with uow.transaction():
        uow.revisions.create(
            Revision(
                revision_id="R2",
                part_id="PART-BACKUP",
                revision_code="REV02",
                created_at=T0 + timedelta(hours=3),
                parent_revision_id="R1",
            ),
            event_id="LC-R2",
        )
    writer.close()

    with SQLiteLifecycleReadOnlySession(database) as fresh:
        assert fresh.snapshot_version == 2
        assert [
            item.revision_id for item in fresh.queries.revision_history("PART-BACKUP")
        ] == ["R1", "R2"]


def test_read_only_session_rejects_stale_projection(tmp_path) -> None:
    database = tmp_path / "source.db"
    _create_committed_database(database)

    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE lifecycle_read_model_meta SET snapshot_version = 0 WHERE singleton = 1"
    )
    connection.commit()
    connection.close()

    with pytest.raises(LifecycleReadOnlyStaleError, match="projection is stale"):
        SQLiteLifecycleReadOnlySession(database)

    repaired = SQLiteLifecycleStore(database)
    repaired.close()
    with SQLiteLifecycleReadOnlySession(database) as session:
        assert session.snapshot_version == session.read_model_version == 1
