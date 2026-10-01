from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from .models import (
    FeatureAnchor,
    MeasurementSession,
    MeasurementType,
    PhysicalMeasurement,
    ProvenanceSource,
)


_LOCAL_SCHEMA_VERSION = "mrea.chat2.measurement-session.local.v1"


class MeasurementSessionRepository(Protocol):
    """Persistence boundary consumed by ``MeasurementSessionService``."""

    def save(self, session: MeasurementSession) -> None: ...

    def get(self, session_id: str) -> MeasurementSession: ...


class InMemoryMeasurementSessionRepository:
    """Ephemeral repository retained for unit tests and short-lived workflows."""

    def __init__(self) -> None:
        self._sessions: dict[str, MeasurementSession] = {}

    def save(self, session: MeasurementSession) -> None:
        self._sessions[session.session_id] = deepcopy(session)

    def get(self, session_id: str) -> MeasurementSession:
        try:
            return deepcopy(self._sessions[session_id])
        except KeyError as exc:
            raise KeyError(f"measurement session not found: {session_id}") from exc


class SqliteMeasurementSessionRepository:
    """Durable local repository for offline-first measurement sessions.

    SQLite owns transactional durability. Chat 2 stores one versioned JSON payload per
    session so the local persistence format remains private to this slice and does not
    become a shared contract by accident.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def save(self, session: MeasurementSession) -> None:
        payload = json.dumps(
            _serialize_session(session),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO measurement_sessions(session_id, schema_version, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (session.session_id, _LOCAL_SCHEMA_VERSION, payload),
            )

    def get(self, session_id: str) -> MeasurementSession:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT schema_version, payload_json FROM measurement_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            raise KeyError(f"measurement session not found: {session_id}")

        schema_version, payload_json = row
        if schema_version != _LOCAL_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported stored measurement-session schema: {schema_version!r}"
            )

        try:
            raw = json.loads(payload_json)
            session = _deserialize_session(raw)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid stored measurement session: {session_id}") from exc

        if session.session_id != session_id:
            raise ValueError("stored measurement session id does not match lookup key")
        return session

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS measurement_sessions(
                    session_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5.0)


def _format_datetime(value: datetime, field_name: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.isoformat()


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _serialize_anchor(anchor: FeatureAnchor) -> dict[str, Any]:
    return {
        "anchor_id": anchor.anchor_id,
        "view_id": anchor.view_id,
        "reference_frame_id": anchor.reference_frame_id,
        "x_px": anchor.x_px,
        "y_px": anchor.y_px,
    }


def _deserialize_anchor(raw: Any) -> FeatureAnchor:
    if not isinstance(raw, dict):
        raise ValueError("stored anchor must be an object")
    return FeatureAnchor(
        anchor_id=raw["anchor_id"],
        view_id=raw["view_id"],
        reference_frame_id=raw["reference_frame_id"],
        x_px=raw["x_px"],
        y_px=raw["y_px"],
    )


def _serialize_measurement(measurement: PhysicalMeasurement) -> dict[str, Any]:
    return {
        "measurement_id": measurement.measurement_id,
        "measurement_type": measurement.measurement_type.value,
        "value": str(measurement.value),
        "unit": measurement.unit,
        "source": measurement.source.value,
        "view_id": measurement.view_id,
        "anchors": [_serialize_anchor(anchor) for anchor in measurement.anchors],
        "evidence_frame_id": measurement.evidence_frame_id,
        "uncertainty": (
            str(measurement.uncertainty) if measurement.uncertainty is not None else None
        ),
        "instrument_type": measurement.instrument_type,
        "confirmed": measurement.confirmed,
        "confirmed_at": (
            _format_datetime(measurement.confirmed_at, "confirmed_at")
            if measurement.confirmed_at is not None
            else None
        ),
        "confirmation_source": (
            measurement.confirmation_source.value
            if measurement.confirmation_source is not None
            else None
        ),
        "created_at": _format_datetime(measurement.created_at, "measurement.created_at"),
    }


def _deserialize_measurement(raw: Any) -> PhysicalMeasurement:
    if not isinstance(raw, dict):
        raise ValueError("stored measurement must be an object")

    raw_anchors = raw["anchors"]
    if not isinstance(raw_anchors, list) or not 1 <= len(raw_anchors) <= 3:
        raise ValueError("stored measurement must contain one to three anchors")
    anchors = [_deserialize_anchor(item) for item in raw_anchors]
    padded: list[FeatureAnchor | None] = [*anchors, *([None] * (3 - len(anchors)))]

    confirmed_at = raw.get("confirmed_at")
    confirmation_source = raw.get("confirmation_source")
    uncertainty = raw.get("uncertainty")

    return PhysicalMeasurement(
        measurement_id=raw["measurement_id"],
        measurement_type=MeasurementType(raw["measurement_type"]),
        value=Decimal(raw["value"]),
        unit=raw["unit"],
        source=ProvenanceSource(raw["source"]),
        view_id=raw["view_id"],
        anchor_a=padded[0],
        anchor_b=padded[1],
        anchor_c=padded[2],
        evidence_frame_id=raw.get("evidence_frame_id"),
        uncertainty=Decimal(uncertainty) if uncertainty is not None else None,
        instrument_type=raw.get("instrument_type"),
        confirmed=raw["confirmed"],
        confirmed_at=(
            _parse_datetime(confirmed_at, "confirmed_at") if confirmed_at is not None else None
        ),
        confirmation_source=(
            ProvenanceSource(confirmation_source)
            if confirmation_source is not None
            else None
        ),
        created_at=_parse_datetime(raw["created_at"], "measurement.created_at"),
    )


def _serialize_session(session: MeasurementSession) -> dict[str, Any]:
    return {
        "schema_version": _LOCAL_SCHEMA_VERSION,
        "session_id": session.session_id,
        "project_id": session.project_id,
        "created_at": _format_datetime(session.created_at, "session.created_at"),
        "measurements": [
            _serialize_measurement(measurement) for measurement in session.measurements
        ],
    }


def _deserialize_session(raw: Any) -> MeasurementSession:
    if not isinstance(raw, dict):
        raise ValueError("stored measurement session must be an object")
    if raw.get("schema_version") != _LOCAL_SCHEMA_VERSION:
        raise ValueError("stored payload schema_version is unsupported")
    measurements = raw["measurements"]
    if not isinstance(measurements, list):
        raise ValueError("stored measurements must be an array")
    return MeasurementSession(
        session_id=raw["session_id"],
        project_id=raw["project_id"],
        measurements=tuple(_deserialize_measurement(item) for item in measurements),
        created_at=_parse_datetime(raw["created_at"], "session.created_at"),
    )
