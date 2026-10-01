from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    InMemoryMeasurementSessionRepository,
    MeasurementSession,
    MeasurementSessionService,
    SqliteMeasurementSessionRepository,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS14-{self._value:03d}"


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


def test_sqlite_list_sessions_survives_reopen_and_filters_project(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = MeasurementSessionService(
        SqliteMeasurementSessionRepository(database_path),
        id_factory=SequentialIds(),
        clock=SequenceClock(
            datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc),
        ),
    )

    first = service.create_session("PROJECT-A")
    second = service.create_session("PROJECT-B")
    third = service.create_session("PROJECT-A")

    reopened = MeasurementSessionService(
        SqliteMeasurementSessionRepository(database_path)
    )

    assert [session.session_id for session in reopened.list_sessions()] == [
        third.session_id,
        second.session_id,
        first.session_id,
    ]
    assert [session.session_id for session in reopened.list_sessions(project_id="PROJECT-A")] == [
        third.session_id,
        first.session_id,
    ]
    assert reopened.list_sessions(project_id="PROJECT-MISSING") == ()


def test_session_order_has_stable_session_id_tie_break(tmp_path: Path) -> None:
    created_at = datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc)
    expected = ["MS-A", "MS-B"]

    repositories = [
        InMemoryMeasurementSessionRepository(),
        SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3"),
    ]
    for repository in repositories:
        repository.save(MeasurementSession("MS-B", "PROJECT-TIE", created_at=created_at))
        repository.save(MeasurementSession("MS-A", "PROJECT-TIE", created_at=created_at))
        assert [session.session_id for session in repository.list_sessions()] == expected


def test_project_filter_is_normalized_and_empty_filter_fails_closed(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")
    repository.save(
        MeasurementSession(
            "MS-001",
            "PROJECT-A",
            created_at=datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc),
        )
    )

    assert [session.session_id for session in repository.list_sessions(project_id="  PROJECT-A  ")] == [
        "MS-001"
    ]
    with pytest.raises(ValueError, match="project_id filter must not be empty"):
        repository.list_sessions(project_id="   ")


def test_corrupt_stored_session_fails_closed_during_enumeration(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    repository = SqliteMeasurementSessionRepository(database_path)
    repository.save(
        MeasurementSession(
            "MS-GOOD",
            "PROJECT-A",
            created_at=datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc),
        )
    )
    repository.save(
        MeasurementSession(
            "MS-BAD",
            "PROJECT-A",
            created_at=datetime(2026, 10, 1, 7, 0, tzinfo=timezone.utc),
        )
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE measurement_sessions SET payload_json = ? WHERE session_id = ?",
            ("{broken-json", "MS-BAD"),
        )

    with pytest.raises(ValueError, match="invalid stored measurement session: MS-BAD"):
        repository.list_sessions()
