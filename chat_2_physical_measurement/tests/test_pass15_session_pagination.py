from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    InMemoryMeasurementSessionRepository,
    MeasurementSession,
    MeasurementSessionPageCursor,
    MeasurementSessionService,
    SqliteMeasurementSessionRepository,
)


SCHEMA_VERSION = "mrea.chat2.measurement-session.local.v1"


def _session(
    session_id: str,
    project_id: str,
    created_at: datetime,
) -> MeasurementSession:
    return MeasurementSession(
        session_id=session_id,
        project_id=project_id,
        created_at=created_at,
    )


def _collect_pages(repository, *, project_id: str | None = None, limit: int = 2):
    collected = []
    cursor = None
    while True:
        page = repository.list_session_page(
            project_id=project_id,
            limit=limit,
            cursor=cursor,
        )
        collected.extend(page.sessions)
        if page.next_cursor is None:
            return collected
        cursor = page.next_cursor


def test_sqlite_keyset_pages_have_no_duplicates_or_gaps_after_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    repository = SqliteMeasurementSessionRepository(database_path)
    base = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    sessions = [
        _session("MS-005", "PROJECT-A", base + timedelta(minutes=5)),
        _session("MS-004", "PROJECT-B", base + timedelta(minutes=4)),
        _session("MS-003", "PROJECT-A", base + timedelta(minutes=3)),
        _session("MS-002", "PROJECT-B", base + timedelta(minutes=2)),
        _session("MS-001", "PROJECT-A", base + timedelta(minutes=1)),
    ]
    for session in sessions:
        repository.save(session)

    reopened = SqliteMeasurementSessionRepository(database_path)
    collected = _collect_pages(reopened, limit=2)

    assert [session.session_id for session in collected] == [
        "MS-005",
        "MS-004",
        "MS-003",
        "MS-002",
        "MS-001",
    ]
    assert len({session.session_id for session in collected}) == 5


def test_project_scoped_pagination_and_cursor_scope_are_deterministic(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")
    created_at = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    for session in (
        _session("MS-A1", "PROJECT-A", created_at + timedelta(minutes=3)),
        _session("MS-B1", "PROJECT-B", created_at + timedelta(minutes=2)),
        _session("MS-A2", "PROJECT-A", created_at + timedelta(minutes=1)),
    ):
        repository.save(session)

    first = repository.list_session_page(project_id=" PROJECT-A ", limit=1)
    assert [session.session_id for session in first.sessions] == ["MS-A1"]
    assert first.next_cursor is not None
    assert first.next_cursor.project_id == "PROJECT-A"

    second = repository.list_session_page(
        project_id="PROJECT-A",
        limit=1,
        cursor=first.next_cursor,
    )
    assert [session.session_id for session in second.sessions] == ["MS-A2"]
    assert second.next_cursor is None

    with pytest.raises(ValueError, match="cursor project scope"):
        repository.list_session_page(
            project_id="PROJECT-B",
            limit=1,
            cursor=first.next_cursor,
        )


def test_equal_timestamp_tie_break_matches_between_backends(tmp_path: Path) -> None:
    created_at = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    expected = ["MS-A", "MS-B", "MS-C"]

    repositories = [
        InMemoryMeasurementSessionRepository(),
        SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3"),
    ]
    for repository in repositories:
        for session_id in ("MS-C", "MS-A", "MS-B"):
            repository.save(_session(session_id, "PROJECT-TIE", created_at))
        collected = _collect_pages(repository, limit=1)
        assert [session.session_id for session in collected] == expected


def test_timezone_offsets_use_absolute_instant_ordering(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")
    repository.save(
        _session(
            "MS-LATER",
            "PROJECT-TZ",
            datetime(2026, 10, 1, 14, 30, tzinfo=timezone(timedelta(hours=3))),
        )
    )
    repository.save(
        _session(
            "MS-EARLIER",
            "PROJECT-TZ",
            datetime(2026, 10, 1, 12, 0, tzinfo=timezone(timedelta(hours=1))),
        )
    )

    assert [session.session_id for session in repository.list_sessions()] == [
        "MS-LATER",
        "MS-EARLIER",
    ]


def test_page_limit_and_cursor_validation_fail_closed(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")

    for invalid_limit in (0, 501, True, 1.5):
        with pytest.raises(ValueError, match="session page limit"):
            repository.list_session_page(limit=invalid_limit)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="cursor.created_at"):
        MeasurementSessionPageCursor(
            created_at=datetime(2026, 10, 1, 12, 0),
            session_id="MS-001",
        )


def test_pass14_database_is_backfilled_for_indexed_pagination(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    created_at = datetime(2026, 10, 1, 13, 0, tzinfo=timezone.utc)
    payload = json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "session_id": "MS-OLD",
            "project_id": "PROJECT-OLD",
            "created_at": created_at.isoformat(),
            "measurements": [],
        }
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE measurement_sessions(
                session_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO measurement_sessions(session_id, schema_version, payload_json) VALUES (?, ?, ?)",
            ("MS-OLD", SCHEMA_VERSION, payload),
        )

    repository = SqliteMeasurementSessionRepository(database_path)
    page = repository.list_session_page(project_id="PROJECT-OLD", limit=10)
    assert [session.session_id for session in page.sessions] == ["MS-OLD"]

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(measurement_sessions)")}
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(measurement_sessions)")}
        metadata = connection.execute(
            "SELECT project_id, created_at_utc_us FROM measurement_sessions WHERE session_id = ?",
            ("MS-OLD",),
        ).fetchone()

    assert {"project_id", "created_at_utc_us"}.issubset(columns)
    assert "idx_measurement_sessions_order" in indexes
    assert "idx_measurement_sessions_project_order" in indexes
    assert metadata is not None
    assert metadata[0] == "PROJECT-OLD"
    assert isinstance(metadata[1], int)


def test_corrupt_legacy_row_fails_closed_during_metadata_migration(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE measurement_sessions(
                session_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO measurement_sessions(session_id, schema_version, payload_json) VALUES (?, ?, ?)",
            ("MS-BAD", SCHEMA_VERSION, "{broken-json"),
        )

    with pytest.raises(ValueError, match="invalid stored measurement session: MS-BAD"):
        SqliteMeasurementSessionRepository(database_path)


def test_query_metadata_drift_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    repository = SqliteMeasurementSessionRepository(database_path)
    repository.save(
        _session(
            "MS-DRIFT",
            "PROJECT-A",
            datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc),
        )
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE measurement_sessions SET created_at_utc_us = created_at_utc_us + 1 WHERE session_id = ?",
            ("MS-DRIFT",),
        )

    with pytest.raises(ValueError, match="stored session query metadata mismatch"):
        repository.list_session_page(limit=10)


def test_service_exposes_same_paged_query_surface(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")
    repository.save(
        _session(
            "MS-SERVICE",
            "PROJECT-SERVICE",
            datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
        )
    )
    service = MeasurementSessionService(repository)

    page = service.list_session_page(project_id="PROJECT-SERVICE", limit=1)
    assert [session.session_id for session in page.sessions] == ["MS-SERVICE"]
    assert page.next_cursor is None
