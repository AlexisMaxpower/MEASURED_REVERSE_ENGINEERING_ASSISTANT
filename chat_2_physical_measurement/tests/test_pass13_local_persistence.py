from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
    SqliteMeasurementSessionRepository,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS13-{self._value:03d}"


def _service(database_path: Path) -> MeasurementSessionService:
    return MeasurementSessionService(
        SqliteMeasurementSessionRepository(database_path),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 10, 1, 1, 45, tzinfo=timezone.utc),
    )


def _anchors(service: MeasurementSessionService, count: int = 2):
    return tuple(
        service.create_manual_anchor(
            view_id="VIEW-FRONT",
            reference_frame_id="REF-FRONT",
            x_px=10.0 + index * 20.0,
            y_px=15.0 + index * 10.0,
        )
        for index in range(count)
    )


def test_pending_candidate_survives_repository_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = _service(database_path)
    session = service.create_session("PROJECT-PASS13")
    a, b = _anchors(service)

    candidate = service.add_reported_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="42.180",
        source=ProvenanceSource.DEVICE_REPORTED,
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        evidence_frame_id="FRAME-001",
        uncertainty="0.015",
        instrument_type="DIGITAL_CALIPER",
    )

    reopened = _service(database_path).get_session(session.session_id)
    restored = reopened.get(candidate.measurement_id)

    assert restored.value == Decimal("42.180")
    assert restored.uncertainty == Decimal("0.015")
    assert restored.source is ProvenanceSource.DEVICE_REPORTED
    assert restored.evidence_frame_id == "FRAME-001"
    assert restored.instrument_type == "DIGITAL_CALIPER"
    assert restored.is_verified is False
    assert restored.confirmation_source is None
    assert [anchor.anchor_id for anchor in restored.anchors] == [a.anchor_id, b.anchor_id]


def test_confirmation_survives_second_repository_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = _service(database_path)
    session = service.create_session("PROJECT-PASS13")
    a, b = _anchors(service)
    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.THICKNESS,
        value="5.20",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        evidence_frame_id="FRAME-002",
    )

    reopened_service = _service(database_path)
    confirmed = reopened_service.confirm_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    restored = _service(database_path).get_session(session.session_id).get(
        candidate.measurement_id
    )
    assert confirmed.is_verified is True
    assert restored.is_verified is True
    assert restored.confirmation_source is ProvenanceSource.USER_CONFIRMED
    assert restored.confirmed_at == datetime(2026, 10, 1, 1, 45, tzinfo=timezone.utc)


def test_three_anchor_angle_and_unit_neutral_uncertainty_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = _service(database_path)
    session = service.create_session("PROJECT-PASS13")
    a, b, c = _anchors(service, 3)

    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="45.500",
        view_id="VIEW-FRONT",
        anchor_a=a,
        anchor_b=b,
        anchor_c=c,
        uncertainty="0.25",
    )

    restored = _service(database_path).get_session(session.session_id).get(
        candidate.measurement_id
    )
    assert restored.measurement_type is MeasurementType.ANGLE
    assert restored.unit == "deg"
    assert restored.value == Decimal("45.500")
    assert restored.uncertainty == Decimal("0.25")
    assert restored.uncertainty_mm is None
    assert [anchor.anchor_id for anchor in restored.anchors] == [
        a.anchor_id,
        b.anchor_id,
        c.anchor_id,
    ]


def test_corrupt_payload_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = _service(database_path)
    session = service.create_session("PROJECT-PASS13")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE measurement_sessions SET payload_json = ? WHERE session_id = ?",
            ("{not-json", session.session_id),
        )

    repository = SqliteMeasurementSessionRepository(database_path)
    with pytest.raises(ValueError, match="invalid stored measurement session"):
        repository.get(session.session_id)


def test_unknown_local_schema_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "measurement_sessions.sqlite3"
    service = _service(database_path)
    session = service.create_session("PROJECT-PASS13")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE measurement_sessions SET schema_version = ? WHERE session_id = ?",
            ("mrea.chat2.measurement-session.local.v999", session.session_id),
        )

    repository = SqliteMeasurementSessionRepository(database_path)
    with pytest.raises(ValueError, match="unsupported stored measurement-session schema"):
        repository.get(session.session_id)


def test_missing_session_keeps_existing_repository_semantics(tmp_path: Path) -> None:
    repository = SqliteMeasurementSessionRepository(tmp_path / "measurement_sessions.sqlite3")

    with pytest.raises(KeyError, match="measurement session not found"):
        repository.get("MS-MISSING")
