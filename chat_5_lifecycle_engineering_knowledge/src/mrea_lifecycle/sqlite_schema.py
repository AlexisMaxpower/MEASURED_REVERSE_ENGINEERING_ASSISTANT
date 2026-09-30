from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Callable, Tuple


SQLITE_RELATIONAL_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class SQLiteSchemaMigration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


def _create_normalized_read_model(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lifecycle_revisions (
            revision_id TEXT PRIMARY KEY,
            part_id TEXT NOT NULL,
            revision_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            parent_revision_id TEXT,
            notes TEXT,
            source_cad_artifact_id TEXT,
            origin TEXT NOT NULL,
            cad_package_id TEXT,
            sketch_package_id TEXT,
            cad_verification_report_id TEXT,
            cad_adapter TEXT,
            verification_status TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS ux_lifecycle_revision_code
            ON lifecycle_revisions(part_id, revision_code);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_revisions_part
            ON lifecycle_revisions(part_id, created_at, revision_id);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_revisions_verification
            ON lifecycle_revisions(origin, verification_status);

        CREATE TABLE IF NOT EXISTS lifecycle_cad_artifacts (
            revision_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            artifact_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            uri TEXT NOT NULL,
            media_type TEXT,
            sha256 TEXT,
            metadata_json TEXT NOT NULL,
            PRIMARY KEY (revision_id, ordinal),
            UNIQUE (revision_id, artifact_id),
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lifecycle_manufacturing (
            manufacturing_id TEXT PRIMARY KEY,
            revision_id TEXT NOT NULL,
            material TEXT NOT NULL,
            method TEXT NOT NULL,
            manufactured_at TEXT NOT NULL,
            batch TEXT,
            machine TEXT,
            print_profile TEXT,
            contractor TEXT,
            cost TEXT,
            post_processing TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_manufacturing_revision
            ON lifecycle_manufacturing(revision_id, manufactured_at);

        CREATE TABLE IF NOT EXISTS lifecycle_physical_instances (
            instance_id TEXT PRIMARY KEY,
            part_id TEXT NOT NULL,
            revision_id TEXT NOT NULL,
            manufacturing_id TEXT NOT NULL,
            material TEXT NOT NULL,
            method TEXT NOT NULL,
            manufactured_at TEXT NOT NULL,
            batch TEXT,
            machine TEXT,
            print_profile TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE,
            FOREIGN KEY (manufacturing_id)
                REFERENCES lifecycle_manufacturing(manufacturing_id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_instances_part
            ON lifecycle_physical_instances(part_id, revision_id);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_instances_manufacturing
            ON lifecycle_physical_instances(manufacturing_id, instance_id);

        CREATE TABLE IF NOT EXISTS lifecycle_installations (
            installation_id TEXT PRIMARY KEY,
            revision_id TEXT NOT NULL,
            manufacturing_id TEXT NOT NULL,
            equipment_id TEXT NOT NULL,
            position TEXT NOT NULL,
            installed_at TEXT NOT NULL,
            technician TEXT,
            notes TEXT,
            instance_id TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE,
            FOREIGN KEY (manufacturing_id)
                REFERENCES lifecycle_manufacturing(manufacturing_id)
                ON DELETE CASCADE,
            FOREIGN KEY (instance_id)
                REFERENCES lifecycle_physical_instances(instance_id)
                ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_installations_equipment
            ON lifecycle_installations(equipment_id, position, installed_at);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_installations_instance
            ON lifecycle_installations(instance_id, installed_at);

        CREATE TABLE IF NOT EXISTS lifecycle_tests (
            test_id TEXT PRIMARY KEY,
            revision_id TEXT NOT NULL,
            tested_at TEXT NOT NULL,
            test_type TEXT NOT NULL,
            conditions TEXT NOT NULL,
            result TEXT NOT NULL,
            conclusion TEXT NOT NULL,
            manufacturing_id TEXT,
            installation_id TEXT,
            instance_id TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE,
            FOREIGN KEY (manufacturing_id)
                REFERENCES lifecycle_manufacturing(manufacturing_id)
                ON DELETE SET NULL,
            FOREIGN KEY (installation_id)
                REFERENCES lifecycle_installations(installation_id)
                ON DELETE SET NULL,
            FOREIGN KEY (instance_id)
                REFERENCES lifecycle_physical_instances(instance_id)
                ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_tests_revision
            ON lifecycle_tests(revision_id, tested_at);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_tests_instance
            ON lifecycle_tests(instance_id, tested_at);

        CREATE TABLE IF NOT EXISTS lifecycle_test_artifacts (
            test_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            artifact_id TEXT NOT NULL,
            PRIMARY KEY (test_id, ordinal),
            FOREIGN KEY (test_id)
                REFERENCES lifecycle_tests(test_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lifecycle_failures (
            failure_id TEXT PRIMARY KEY,
            revision_id TEXT NOT NULL,
            failed_at TEXT NOT NULL,
            failure_type TEXT NOT NULL,
            damage_location TEXT NOT NULL,
            circumstances TEXT NOT NULL,
            manufacturing_id TEXT,
            installation_id TEXT,
            estimated_cause TEXT,
            confirmed_cause TEXT,
            related_feature TEXT,
            instance_id TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE,
            FOREIGN KEY (manufacturing_id)
                REFERENCES lifecycle_manufacturing(manufacturing_id)
                ON DELETE SET NULL,
            FOREIGN KEY (installation_id)
                REFERENCES lifecycle_installations(installation_id)
                ON DELETE SET NULL,
            FOREIGN KEY (instance_id)
                REFERENCES lifecycle_physical_instances(instance_id)
                ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_failures_revision
            ON lifecycle_failures(revision_id, failed_at);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_failures_instance
            ON lifecycle_failures(instance_id, failed_at);

        CREATE TABLE IF NOT EXISTS lifecycle_failure_evidence (
            failure_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            artifact_id TEXT NOT NULL,
            PRIMARY KEY (failure_id, ordinal),
            FOREIGN KEY (failure_id)
                REFERENCES lifecycle_failures(failure_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lifecycle_events_relational (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence INTEGER NOT NULL UNIQUE,
            revision_id TEXT NOT NULL,
            manufacturing_id TEXT,
            installation_id TEXT,
            test_id TEXT,
            failure_id TEXT,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_events_revision
            ON lifecycle_events_relational(revision_id, sequence);

        CREATE TABLE IF NOT EXISTS lifecycle_physical_events_relational (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence INTEGER NOT NULL UNIQUE,
            instance_id TEXT NOT NULL,
            revision_id TEXT NOT NULL,
            manufacturing_id TEXT NOT NULL,
            installation_id TEXT,
            test_id TEXT,
            failure_id TEXT,
            equipment_id TEXT,
            position TEXT,
            test_outcome TEXT,
            replacement_instance_id TEXT,
            notes TEXT,
            FOREIGN KEY (instance_id)
                REFERENCES lifecycle_physical_instances(instance_id)
                ON DELETE CASCADE,
            FOREIGN KEY (revision_id)
                REFERENCES lifecycle_revisions(revision_id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_physical_events_instance
            ON lifecycle_physical_events_relational(instance_id, sequence);
        CREATE INDEX IF NOT EXISTS ix_lifecycle_physical_events_equipment
            ON lifecycle_physical_events_relational(
                equipment_id, position, sequence
            );

        CREATE TABLE IF NOT EXISTS lifecycle_read_model_meta (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            snapshot_version INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO lifecycle_read_model_meta(
            singleton, snapshot_version
        ) VALUES (1, -1);
        """
    )


SQLITE_MIGRATIONS: Tuple[SQLiteSchemaMigration, ...] = (
    SQLiteSchemaMigration(
        version=2,
        name="normalized_lifecycle_read_model",
        apply=_create_normalized_read_model,
    ),
)


class SQLiteSchemaManager:
    """Small deterministic migration runner for Chat 5 SQLite persistence."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def _ensure_journal(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

    @property
    def current_version(self) -> int:
        self._ensure_journal()
        row = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM lifecycle_schema_migrations"
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def migrate(self) -> tuple[int, ...]:
        self._ensure_journal()
        applied_rows = self.connection.execute(
            "SELECT version FROM lifecycle_schema_migrations"
        ).fetchall()
        applied = {int(row[0]) for row in applied_rows}
        newly_applied: list[int] = []

        for migration in SQLITE_MIGRATIONS:
            if migration.version in applied:
                continue
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                migration.apply(self.connection)
                self.connection.execute(
                    """
                    INSERT INTO lifecycle_schema_migrations(version, name)
                    VALUES (?, ?)
                    """,
                    (migration.version, migration.name),
                )
                self.connection.execute(
                    f"PRAGMA user_version = {migration.version}"
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            newly_applied.append(migration.version)
            applied.add(migration.version)

        return tuple(newly_applied)
