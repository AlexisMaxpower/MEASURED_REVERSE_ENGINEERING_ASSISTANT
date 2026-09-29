from __future__ import annotations

from pathlib import Path
import sqlite3

from .engineering_knowledge import SQLiteEngineeringKnowledgeRepository
from .persistence import SQLITE_SNAPSHOT_SCHEMA_VERSION
from .relational import SQLiteLifecycleQueryRepository
from .sqlite_schema import SQLITE_RELATIONAL_SCHEMA_VERSION


class LifecycleReadOnlyError(RuntimeError):
    pass


class LifecycleReadOnlyStaleError(LifecycleReadOnlyError):
    pass


def _readonly_uri(database: Path) -> str:
    return f"{database.resolve().as_uri()}?mode=ro"


class SQLiteLifecycleReadOnlySession:
    """Read-only SQL-native lifecycle and engineering knowledge query session.

    The session never opens a writable SQLite handle. It also refuses to serve a
    relational projection that does not represent the current authoritative snapshot.
    """

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self._connection: sqlite3.Connection | None = None
        self._queries: SQLiteLifecycleQueryRepository | None = None
        self._knowledge: SQLiteEngineeringKnowledgeRepository | None = None
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

        self._connection = connection
        self._queries = SQLiteLifecycleQueryRepository(connection)
        self._knowledge = SQLiteEngineeringKnowledgeRepository(connection)
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
    def knowledge(self) -> SQLiteEngineeringKnowledgeRepository:
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
