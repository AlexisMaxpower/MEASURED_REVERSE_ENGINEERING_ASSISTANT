from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Optional
from uuid import uuid4

from .persistence import SQLITE_SNAPSHOT_SCHEMA_VERSION
from .sqlite_schema import SQLITE_RELATIONAL_SCHEMA_VERSION


LIFECYCLE_BACKUP_FORMAT_VERSION = "mrea.lifecycle-backup.v1"


class LifecycleBackupError(RuntimeError):
    pass


class LifecycleBackupConsistencyError(LifecycleBackupError):
    pass


class LifecycleBackupIntegrityError(LifecycleBackupError):
    pass


@dataclass(frozen=True, slots=True)
class LifecycleDatabaseInspection:
    snapshot_schema_version: str
    snapshot_version: int
    read_model_version: int
    relational_schema_version: int


@dataclass(frozen=True, slots=True)
class LifecycleBackupManifest:
    format_version: str
    created_at: str
    snapshot_schema_version: str
    snapshot_version: int
    read_model_version: int
    relational_schema_version: int
    sha256: str
    size_bytes: int

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LifecycleBackupManifest":
        try:
            return cls(
                format_version=str(payload["format_version"]),
                created_at=str(payload["created_at"]),
                snapshot_schema_version=str(payload["snapshot_schema_version"]),
                snapshot_version=int(payload["snapshot_version"]),
                read_model_version=int(payload["read_model_version"]),
                relational_schema_version=int(payload["relational_schema_version"]),
                sha256=str(payload["sha256"]),
                size_bytes=int(payload["size_bytes"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LifecycleBackupIntegrityError("invalid lifecycle backup manifest") from exc

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LifecycleBackupVerification:
    manifest: LifecycleBackupManifest
    inspection: LifecycleDatabaseInspection


def _readonly_uri(database: Path) -> str:
    return f"{database.resolve().as_uri()}?mode=ro"


def _open_readonly(database: Path) -> sqlite3.Connection:
    if not database.exists() or not database.is_file():
        raise LifecycleBackupError(f"lifecycle database does not exist: {database}")
    try:
        connection = sqlite3.connect(
            _readonly_uri(database),
            uri=True,
            isolation_level=None,
        )
    except sqlite3.Error as exc:
        raise LifecycleBackupError(f"cannot open lifecycle database: {database}") from exc
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA query_only = ON")
    return connection


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_manifest_path(backup_path: Path) -> Path:
    return backup_path.with_name(f"{backup_path.name}.manifest.json")


def _integrity_check(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA integrity_check").fetchall()
    if rows != [("ok",)]:
        raise LifecycleBackupIntegrityError(
            f"SQLite integrity_check failed: {rows!r}"
        )
    foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_rows:
        raise LifecycleBackupIntegrityError(
            f"SQLite foreign_key_check failed: {foreign_key_rows!r}"
        )


def inspect_lifecycle_database(database: str | Path) -> LifecycleDatabaseInspection:
    path = Path(database)
    connection = _open_readonly(path)
    try:
        _integrity_check(connection)
        snapshot_row = connection.execute(
            """
            SELECT schema_version, version
            FROM lifecycle_store
            WHERE singleton = 1
            """
        ).fetchone()
        read_model_row = connection.execute(
            """
            SELECT snapshot_version
            FROM lifecycle_read_model_meta
            WHERE singleton = 1
            """
        ).fetchone()
        migration_row = connection.execute(
            """
            SELECT COALESCE(MAX(version), 0)
            FROM lifecycle_schema_migrations
            """
        ).fetchone()
    except sqlite3.Error as exc:
        raise LifecycleBackupIntegrityError(
            "database is missing required lifecycle persistence structures"
        ) from exc
    finally:
        connection.close()

    if snapshot_row is None or read_model_row is None or migration_row is None:
        raise LifecycleBackupIntegrityError(
            "database is missing required lifecycle persistence metadata"
        )

    inspection = LifecycleDatabaseInspection(
        snapshot_schema_version=str(snapshot_row[0]),
        snapshot_version=int(snapshot_row[1]),
        read_model_version=int(read_model_row[0]),
        relational_schema_version=int(migration_row[0]),
    )

    if inspection.snapshot_schema_version != SQLITE_SNAPSHOT_SCHEMA_VERSION:
        raise LifecycleBackupIntegrityError(
            "unsupported lifecycle snapshot schema: "
            f"{inspection.snapshot_schema_version}"
        )
    if inspection.relational_schema_version != SQLITE_RELATIONAL_SCHEMA_VERSION:
        raise LifecycleBackupIntegrityError(
            "unsupported lifecycle relational schema: "
            f"{inspection.relational_schema_version}"
        )
    if inspection.snapshot_version != inspection.read_model_version:
        raise LifecycleBackupConsistencyError(
            "lifecycle snapshot/read-model version mismatch: "
            f"snapshot={inspection.snapshot_version}, "
            f"read_model={inspection.read_model_version}"
        )
    return inspection


class LifecycleBackupManager:
    """Consistent backup/verification/restore for file-backed lifecycle SQLite DBs."""

    @staticmethod
    def create_backup(
        database: str | Path,
        backup_path: str | Path,
        *,
        manifest_path: Optional[str | Path] = None,
        overwrite: bool = False,
        created_at: Optional[datetime] = None,
    ) -> LifecycleBackupManifest:
        source = Path(database)
        destination = Path(backup_path)
        manifest_destination = (
            Path(manifest_path)
            if manifest_path is not None
            else _default_manifest_path(destination)
        )

        if source.resolve() == destination.resolve():
            raise LifecycleBackupError("backup destination must differ from source")
        if destination.exists() and not overwrite:
            raise LifecycleBackupError(f"backup already exists: {destination}")
        if manifest_destination.exists() and not overwrite:
            raise LifecycleBackupError(
                f"backup manifest already exists: {manifest_destination}"
            )

        source_inspection = inspect_lifecycle_database(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)

        temp_backup = destination.with_name(
            f".{destination.name}.{uuid4().hex}.tmp"
        )
        temp_manifest = manifest_destination.with_name(
            f".{manifest_destination.name}.{uuid4().hex}.tmp"
        )

        source_connection = _open_readonly(source)
        target_connection: Optional[sqlite3.Connection] = None
        try:
            target_connection = sqlite3.connect(temp_backup)
            source_connection.backup(target_connection)
            target_connection.commit()
        except sqlite3.Error as exc:
            raise LifecycleBackupError("SQLite backup operation failed") from exc
        finally:
            source_connection.close()
            if target_connection is not None:
                target_connection.close()

        try:
            backup_inspection = inspect_lifecycle_database(temp_backup)
            if backup_inspection != source_inspection:
                raise LifecycleBackupConsistencyError(
                    "backup metadata differs from source committed state"
                )

            timestamp = created_at or datetime.now(timezone.utc)
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise LifecycleBackupError("backup created_at must be timezone-aware")
            timestamp = timestamp.astimezone(timezone.utc)

            manifest = LifecycleBackupManifest(
                format_version=LIFECYCLE_BACKUP_FORMAT_VERSION,
                created_at=timestamp.isoformat().replace("+00:00", "Z"),
                snapshot_schema_version=backup_inspection.snapshot_schema_version,
                snapshot_version=backup_inspection.snapshot_version,
                read_model_version=backup_inspection.read_model_version,
                relational_schema_version=backup_inspection.relational_schema_version,
                sha256=_sha256(temp_backup),
                size_bytes=temp_backup.stat().st_size,
            )
            temp_manifest.write_text(
                json.dumps(
                    manifest.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            os.replace(temp_backup, destination)
            os.replace(temp_manifest, manifest_destination)
            return manifest
        except Exception:
            temp_backup.unlink(missing_ok=True)
            temp_manifest.unlink(missing_ok=True)
            raise

    @staticmethod
    def load_manifest(
        backup_path: str | Path,
        *,
        manifest_path: Optional[str | Path] = None,
    ) -> LifecycleBackupManifest:
        backup = Path(backup_path)
        manifest = (
            Path(manifest_path)
            if manifest_path is not None
            else _default_manifest_path(backup)
        )
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LifecycleBackupIntegrityError(
                f"cannot read lifecycle backup manifest: {manifest}"
            ) from exc
        if not isinstance(raw, dict):
            raise LifecycleBackupIntegrityError(
                "lifecycle backup manifest must be a JSON object"
            )
        parsed = LifecycleBackupManifest.from_dict(raw)
        if parsed.format_version != LIFECYCLE_BACKUP_FORMAT_VERSION:
            raise LifecycleBackupIntegrityError(
                f"unsupported lifecycle backup format: {parsed.format_version}"
            )
        return parsed

    @classmethod
    def verify_backup(
        cls,
        backup_path: str | Path,
        *,
        manifest_path: Optional[str | Path] = None,
    ) -> LifecycleBackupVerification:
        backup = Path(backup_path)
        manifest = cls.load_manifest(backup, manifest_path=manifest_path)
        if not backup.exists() or not backup.is_file():
            raise LifecycleBackupIntegrityError(
                f"lifecycle backup does not exist: {backup}"
            )
        actual_size = backup.stat().st_size
        if actual_size != manifest.size_bytes:
            raise LifecycleBackupIntegrityError(
                "lifecycle backup size mismatch: "
                f"manifest={manifest.size_bytes}, actual={actual_size}"
            )
        actual_sha256 = _sha256(backup)
        if actual_sha256 != manifest.sha256:
            raise LifecycleBackupIntegrityError(
                "lifecycle backup SHA-256 mismatch"
            )

        inspection = inspect_lifecycle_database(backup)
        if (
            inspection.snapshot_schema_version != manifest.snapshot_schema_version
            or inspection.snapshot_version != manifest.snapshot_version
            or inspection.read_model_version != manifest.read_model_version
            or inspection.relational_schema_version
            != manifest.relational_schema_version
        ):
            raise LifecycleBackupConsistencyError(
                "lifecycle backup metadata does not match manifest"
            )
        return LifecycleBackupVerification(
            manifest=manifest,
            inspection=inspection,
        )

    @classmethod
    def restore_backup(
        cls,
        backup_path: str | Path,
        destination: str | Path,
        *,
        manifest_path: Optional[str | Path] = None,
        overwrite: bool = False,
    ) -> LifecycleBackupManifest:
        backup = Path(backup_path)
        target = Path(destination)
        verification = cls.verify_backup(
            backup,
            manifest_path=manifest_path,
        )
        if backup.resolve() == target.resolve():
            raise LifecycleBackupError("restore destination must differ from backup")
        if target.exists() and not overwrite:
            raise LifecycleBackupError(
                f"restore destination already exists: {target}"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f".{target.name}.{uuid4().hex}.restore.tmp")
        source_connection = _open_readonly(backup)
        target_connection: Optional[sqlite3.Connection] = None
        try:
            target_connection = sqlite3.connect(temp_target)
            source_connection.backup(target_connection)
            target_connection.commit()
        except sqlite3.Error as exc:
            temp_target.unlink(missing_ok=True)
            raise LifecycleBackupError("SQLite restore operation failed") from exc
        finally:
            source_connection.close()
            if target_connection is not None:
                target_connection.close()

        try:
            restored_inspection = inspect_lifecycle_database(temp_target)
            if restored_inspection != verification.inspection:
                raise LifecycleBackupConsistencyError(
                    "restored lifecycle database differs from verified backup"
                )
            os.replace(temp_target, target)
        except Exception:
            temp_target.unlink(missing_ok=True)
            raise
        return verification.manifest
