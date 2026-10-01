from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .persistence import SQLITE_SNAPSHOT_SCHEMA_VERSION
from .relational import SQLiteLifecycleQueryRepository
from .revision_comparison import SQLiteRevisionComparisonEngineeringKnowledgeRepository
from .sqlite_schema import SQLITE_RELATIONAL_SCHEMA_VERSION


class LifecycleReadOnlyError(RuntimeError):
    pass


class LifecycleReadOnlyStaleError(LifecycleReadOnlyError):
    pass


def _readonly_uri(database: Path) -> str:
    return f"{database.resolve().as_uri()}?mode=ro"


class _SnapshotGuardedCursor:
    """Cursor facade that refuses to return rows after snapshot drift."""

    def __init__(
        self,
        cursor: sqlite3.Cursor,
        connection: "_SnapshotGuardedConnection",
    ) -> None:
        self._cursor = cursor
        self._connection = connection

    def fetchone(self) -> Any:
        row = self._cursor.fetchone()
        self._connection.assert_current()
        return row

    def fetchall(self) -> list[Any]:
        rows = self._cursor.fetchall()
        self._connection.assert_current()
        return rows

    def __iter__(self):
        rows = self.fetchall()
        return iter(rows)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class _SnapshotGuardedConnection:
    """Read-only connection facade bound to one accepted lifecycle snapshot.

    SQLite read-only connections opened in autocommit mode do not remain pinned to
    the database version observed when the session was constructed. A later writer
    commit can otherwise make the same long-lived session read newer rows while its
    cached ``snapshot_version`` still identifies the old generation.

    Every repository statement is therefore checked immediately before execution and
    again after its result rows are fetched. If the authoritative snapshot, normalized
    read-model generation or relational schema changed at any point, no rows are
    returned and the caller must refresh/reopen the session. The guard deliberately
    avoids a long-lived read transaction, so an idle read-only session does not hold a
    rollback-journal read lock that would block writers.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        snapshot_schema_version: str,
        snapshot_version: int,
        read_model_version: int,
        relational_schema_version: int,
    ) -> None:
        self._connection = connection
        self._expected_snapshot_schema_version = snapshot_schema_version
        self._expected_snapshot_version = snapshot_version
        self._expected_read_model_version = read_model_version
        self._expected_relational_schema_version = relational_schema_version

    def _current_metadata(self) -> tuple[str, int, int, int]:
        try:
            row = self._connection.execute(
                """
                SELECT s.schema_version,
                       s.version,
                       m.snapshot_version,
                       (
                           SELECT COALESCE(MAX(version), 0)
                           FROM lifecycle_schema_migrations
                       )
                FROM lifecycle_store AS s
                JOIN lifecycle_read_model_meta AS m
                  ON m.singleton = 1
                WHERE s.singleton = 1
                """
            ).fetchone()
        except sqlite3.Error as exc:
            raise LifecycleReadOnlyError(
                "cannot verify lifecycle read-only snapshot metadata"
            ) from exc
        if row is None:
            raise LifecycleReadOnlyError(
                "lifecycle database is missing required persistence metadata"
            )
        return str(row[0]), int(row[1]), int(row[2]), int(row[3])

    def assert_current(self) -> None:
        (
            snapshot_schema_version,
            snapshot_version,
            read_model_version,
            relational_schema_version,
        ) = self._current_metadata()

        if (
            snapshot_schema_version != self._expected_snapshot_schema_version
            or relational_schema_version != self._expected_relational_schema_version
            or snapshot_version != self._expected_snapshot_version
            or read_model_version != self._expected_read_model_version
            or snapshot_version != read_model_version
        ):
            raise LifecycleReadOnlyStaleError(
                "read-only lifecycle session snapshot changed; refresh required: "
                f"expected_snapshot={self._expected_snapshot_version}, "
                f"expected_read_model={self._expected_read_model_version}, "
                f"current_snapshot={snapshot_version}, "
                f"current_read_model={read_model_version}, "
                f"expected_relational_schema={self._expected_relational_schema_version}, "
                f"current_relational_schema={relational_schema_version}"
            )

    def execute(
        self,
        sql: str,
        parameters: tuple[object, ...] | list[object] = (),
    ) -> _SnapshotGuardedCursor:
        self.assert_current()
        cursor = self._connection.execute(sql, parameters)
        return _SnapshotGuardedCursor(cursor, self)


class SQLiteLifecycleReadOnlySession:
    """Read-only SQL-native lifecycle and engineering knowledge query session.

    The session never opens a writable SQLite handle. It also refuses to serve a
    relational projection that does not represent the current authoritative snapshot.
    Repository reads are bound to the snapshot accepted at session open and fail closed
    after external snapshot drift until ``refresh()`` is called. Revision/failure
    analytical queries use snapshot-synchronized materialized rows; durable revision
    comparison and other factual reads share the same guarded snapshot generation.
    """

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self._connection: sqlite3.Connection | None = None
        self._queries: SQLiteLifecycleQueryRepository | None = None
        self._knowledge: SQLiteRevisionComparisonEngineeringKnowledgeRepository | None = None
        self._snapshot_version = 0
        self._read_model_version = 0
        self._relational_schema_version = 0
        self._open()

    def _open(self) -> None:
        if not self.database.exists() or not self.database.is_file():
            raise LifecycleReadOnlyError(
                f"lifecycle database does not exist: {self.database}"
            )
        try:
            connection = sqlite3.connect(
                _readonly_uri(self.database),
                uri=True,
                isolation_level=None,
            )
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA query_only = ON")
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
            try:
                connection.close()
            except UnboundLocalError:
                pass
            raise LifecycleReadOnlyError(
                "cannot open lifecycle database as current read-only store"
            ) from exc

        if snapshot_row is None or read_model_row is None or migration_row is None:
            connection.close()
            raise LifecycleReadOnlyError(
                "lifecycle database is missing required persistence metadata"
            )

        snapshot_schema = str(snapshot_row[0])
        snapshot_version = int(snapshot_row[1])
        read_model_version = int(read_model_row[0])
        relational_schema_version = int(migration_row[0])

        if snapshot_schema != SQLITE_SNAPSHOT_SCHEMA_VERSION:
            connection.close()
            raise LifecycleReadOnlyError(
                f"unsupported lifecycle snapshot schema: {snapshot_schema}"
            )
        if relational_schema_version != SQLITE_RELATIONAL_SCHEMA_VERSION:
            connection.close()
            raise LifecycleReadOnlyError(
                "unsupported lifecycle relational schema: "
                f"{relational_schema_version}"
            )
        if snapshot_version != read_model_version:
            connection.close()
            raise LifecycleReadOnlyStaleError(
                "read-only lifecycle projection is stale: "
                f"snapshot={snapshot_version}, read_model={read_model_version}"
            )

        guarded_connection = _SnapshotGuardedConnection(
            connection,
            snapshot_schema_version=snapshot_schema,
            snapshot_version=snapshot_version,
            read_model_version=read_model_version,
            relational_schema_version=relational_schema_version,
        )
        self._connection = connection
        self._queries = SQLiteLifecycleQueryRepository(guarded_connection)  # type: ignore[arg-type]
        self._knowledge = SQLiteRevisionComparisonEngineeringKnowledgeRepository(
            guarded_connection,  # type: ignore[arg-type]
            snapshot_version=snapshot_version,
        )
        self._snapshot_version = snapshot_version
        self._read_model_version = read_model_version
        self._relational_schema_version = relational_schema_version

    @property
    def snapshot_version(self) -> int:
        return self._snapshot_version

    @property
    def read_model_version(self) -> int:
        return self._read_model_version

    @property
    def relational_schema_version(self) -> int:
        return self._relational_schema_version

    @property
    def queries(self) -> SQLiteLifecycleQueryRepository:
        if self._queries is None:
            raise LifecycleReadOnlyError("read-only lifecycle session is closed")
        return self._queries

    @property
    def knowledge(self) -> SQLiteRevisionComparisonEngineeringKnowledgeRepository:
        if self._knowledge is None:
            raise LifecycleReadOnlyError("read-only lifecycle session is closed")
        return self._knowledge

    def refresh(self) -> int:
        self.close()
        self._open()
        return self._snapshot_version

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._queries = None
        self._knowledge = None

    def __enter__(self) -> "SQLiteLifecycleReadOnlySession":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
