from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Callable, Tuple


SQLITE_RELATIONAL_SCHEMA_VERSION = 4


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


def _add_cad_runtime_truth_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(lifecycle_revisions)").fetchall()
    }
    if "runtime_status" not in columns:
        connection.execute(
            "ALTER TABLE lifecycle_revisions ADD COLUMN runtime_status TEXT"
        )
    if "runtime_evidence_schema_version" not in columns:
        connection.execute(
            "ALTER TABLE lifecycle_revisions "
            "ADD COLUMN runtime_evidence_schema_version TEXT"
        )
    if "runtime_real_host_executed" not in columns:
        connection.execute(
            "ALTER TABLE lifecycle_revisions "
            "ADD COLUMN runtime_real_host_executed INTEGER"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_lifecycle_revisions_runtime_verification "
        "ON lifecycle_revisions(origin, verification_status, runtime_status)"
    )


def _add_materialized_knowledge_aggregates(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lifecycle_revision_outcomes_materialized (
            revision_id TEXT PRIMARY KEY,
            part_id TEXT NOT NULL,
            revision_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            manufacturing_records INTEGER NOT NULL CHECK (manufacturing_records >= 0),
            physical_instances INTEGER NOT NULL CHECK (physical_instances >= 0),
            activated_instances INTEGER NOT NULL CHECK (activated_instances >= 0),
            failed_instances INTEGER NOT NULL CHECK (failed_instances >= 0),
            removed_instances INTEGER NOT NULL CHECK (removed_instances >= 0),
            superseded_instances INTEGER NOT NULL CHECK (superseded_instances >= 0),
            failure_records INTEGER NOT NULL CHECK (failure_records >= 0)
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_revision_outcomes_materialized_part
            ON lifecycle_revision_outcomes_materialized(
                part_id, created_at, revision_id
            );

        CREATE TABLE IF NOT EXISTS lifecycle_failure_patterns_materialized (
            scope_type TEXT NOT NULL
                CHECK (scope_type IN ('GLOBAL', 'PART', 'REVISION')),
            scope_id TEXT NOT NULL,
            part_id TEXT,
            revision_id TEXT,
            failure_type TEXT NOT NULL,
            damage_location TEXT NOT NULL,
            confirmed_cause TEXT,
            occurrence_count INTEGER NOT NULL CHECK (occurrence_count > 0),
            revision_count INTEGER NOT NULL CHECK (revision_count > 0),
            instance_count INTEGER NOT NULL CHECK (instance_count >= 0),
            first_failed_at TEXT NOT NULL,
            last_failed_at TEXT NOT NULL,
            cause_null_rank INTEGER NOT NULL CHECK (cause_null_rank IN (0, 1)),
            cause_sort TEXT NOT NULL,
            PRIMARY KEY (
                scope_type,
                scope_id,
                failure_type,
                damage_location,
                cause_null_rank,
                cause_sort
            )
        );
        CREATE INDEX IF NOT EXISTS ix_lifecycle_failure_patterns_materialized_scope
            ON lifecycle_failure_patterns_materialized(
                scope_type,
                scope_id,
                occurrence_count DESC,
                failure_type,
                damage_location,
                cause_null_rank,
                cause_sort
            );

        UPDATE lifecycle_read_model_meta
        SET snapshot_version = -1
        WHERE singleton = 1;

        CREATE TRIGGER IF NOT EXISTS trg_lifecycle_refresh_materialized_knowledge
        AFTER UPDATE OF snapshot_version ON lifecycle_read_model_meta
        FOR EACH ROW
        BEGIN
            DELETE FROM lifecycle_revision_outcomes_materialized;
            INSERT INTO lifecycle_revision_outcomes_materialized(
                revision_id,
                part_id,
                revision_code,
                created_at,
                manufacturing_records,
                physical_instances,
                activated_instances,
                failed_instances,
                removed_instances,
                superseded_instances,
                failure_records
            )
            SELECT r.revision_id,
                   r.part_id,
                   r.revision_code,
                   r.created_at,
                   COUNT(DISTINCT m.manufacturing_id),
                   COUNT(DISTINCT pi.instance_id),
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'ACTIVATED'
                                       THEN pe.instance_id END),
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'FAILED'
                                       THEN pe.instance_id END),
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'REMOVED'
                                       THEN pe.instance_id END),
                   COUNT(DISTINCT CASE WHEN pe.event_type = 'SUPERSEDED'
                                       THEN pe.instance_id END),
                   COUNT(DISTINCT f.failure_id)
            FROM lifecycle_revisions AS r
            LEFT JOIN lifecycle_manufacturing AS m
                   ON m.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_instances AS pi
                   ON pi.revision_id = r.revision_id
            LEFT JOIN lifecycle_physical_events_relational AS pe
                   ON pe.instance_id = pi.instance_id
            LEFT JOIN lifecycle_failures AS f
                   ON f.revision_id = r.revision_id
            GROUP BY r.revision_id, r.part_id, r.revision_code, r.created_at;

            DELETE FROM lifecycle_failure_patterns_materialized;

            INSERT INTO lifecycle_failure_patterns_materialized(
                scope_type, scope_id, part_id, revision_id,
                failure_type, damage_location, confirmed_cause,
                occurrence_count, revision_count, instance_count,
                first_failed_at, last_failed_at, cause_null_rank, cause_sort
            )
            SELECT 'GLOBAL', '*', NULL, NULL,
                   f.failure_type, f.damage_location, f.confirmed_cause,
                   COUNT(*),
                   COUNT(DISTINCT f.revision_id),
                   COUNT(DISTINCT f.instance_id),
                   MIN(f.failed_at),
                   MAX(f.failed_at),
                   CASE WHEN f.confirmed_cause IS NULL THEN 0 ELSE 1 END,
                   COALESCE(f.confirmed_cause, '')
            FROM lifecycle_failures AS f
            GROUP BY f.failure_type, f.damage_location, f.confirmed_cause;

            INSERT INTO lifecycle_failure_patterns_materialized(
                scope_type, scope_id, part_id, revision_id,
                failure_type, damage_location, confirmed_cause,
                occurrence_count, revision_count, instance_count,
                first_failed_at, last_failed_at, cause_null_rank, cause_sort
            )
            SELECT 'PART', r.part_id, r.part_id, NULL,
                   f.failure_type, f.damage_location, f.confirmed_cause,
                   COUNT(*),
                   COUNT(DISTINCT f.revision_id),
                   COUNT(DISTINCT f.instance_id),
                   MIN(f.failed_at),
                   MAX(f.failed_at),
                   CASE WHEN f.confirmed_cause IS NULL THEN 0 ELSE 1 END,
                   COALESCE(f.confirmed_cause, '')
            FROM lifecycle_failures AS f
            JOIN lifecycle_revisions AS r
              ON r.revision_id = f.revision_id
            GROUP BY r.part_id,
                     f.failure_type,
                     f.damage_location,
                     f.confirmed_cause;

            INSERT INTO lifecycle_failure_patterns_materialized(
                scope_type, scope_id, part_id, revision_id,
                failure_type, damage_location, confirmed_cause,
                occurrence_count, revision_count, instance_count,
                first_failed_at, last_failed_at, cause_null_rank, cause_sort
            )
            SELECT 'REVISION', f.revision_id, r.part_id, f.revision_id,
                   f.failure_type, f.damage_location, f.confirmed_cause,
                   COUNT(*),
                   COUNT(DISTINCT f.revision_id),
                   COUNT(DISTINCT f.instance_id),
                   MIN(f.failed_at),
                   MAX(f.failed_at),
                   CASE WHEN f.confirmed_cause IS NULL THEN 0 ELSE 1 END,
                   COALESCE(f.confirmed_cause, '')
            FROM lifecycle_failures AS f
            JOIN lifecycle_revisions AS r
              ON r.revision_id = f.revision_id
            GROUP BY f.revision_id,
                     r.part_id,
                     f.failure_type,
                     f.damage_location,
                     f.confirmed_cause;
        END;
        """
    )


SQLITE_MIGRATIONS: Tuple[SQLiteSchemaMigration, ...] = (
    SQLiteSchemaMigration(
        version=2,
        name="normalized_lifecycle_read_model",
        apply=_create_normalized_read_model,
    ),
    SQLiteSchemaMigration(
        version=3,
        name="cad_runtime_truth",
        apply=_add_cad_runtime_truth_columns,
    ),
    SQLiteSchemaMigration(
        version=4,
        name="materialized_engineering_knowledge",
        apply=_add_materialized_knowledge_aggregates,
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
