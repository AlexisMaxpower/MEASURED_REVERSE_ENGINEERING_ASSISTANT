from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
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
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 500
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class MeasurementSessionPageCursor:
    created_at: datetime
    session_id: str
    project_id: str | None = None

    def __post_init__(self) -> None:
        _require_aware_datetime(self.created_at, "cursor.created_at")
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("cursor.session_id must be a non-empty string")
        object.__setattr__(self, "project_id", _normalize_project_id(self.project_id))


@dataclass(frozen=True, slots=True)
class MeasurementSessionPage:
    sessions: tuple[MeasurementSession, ...]
    next_cursor: MeasurementSessionPageCursor | None = None

    def __post_init__(self) -> None:
        if not self.sessions and self.next_cursor is not None:
            raise ValueError("empty session page cannot carry next_cursor")


class MeasurementSessionRepository(Protocol):
    """Persistence boundary consumed by ``MeasurementSessionService``."""

    def save(self, session: MeasurementSession) -> None: ...

    def get(self, session_id: str) -> MeasurementSession: ...

    def list_sessions(
        self, *, project_id: str | None = None
    ) -> tuple[MeasurementSession, ...]: ...

    def list_session_page(
        self,
        *,
        project_id: str | None = None,
        limit: int = _DEFAULT_PAGE_SIZE,
        cursor: MeasurementSessionPageCursor | None = None,
    ) -> MeasurementSessionPage: ...


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

    def list_sessions(
        self, *, project_id: str | None = None
    ) -> tuple[MeasurementSession, ...]:
        normalized_project_id = _normalize_project_id(project_id)
        sessions = [deepcopy(session) for session in self._sessions.values()]
        return _filter_and_sort_sessions(sessions, project_id=normalized_project_id)

    def list_session_page(
        self,
        *,
        project_id: str | None = None,
        limit: int = _DEFAULT_PAGE_SIZE,
        cursor: MeasurementSessionPageCursor | None = None,
    ) -> MeasurementSessionPage:
        normalized_project_id = _normalize_project_id(project_id)
        normalized_limit = _normalize_page_limit(limit)
        _validate_cursor_scope(cursor, normalized_project_id)

        sessions = [deepcopy(session) for session in self._sessions.values()]
        ordered = list(_filter_and_sort_sessions(sessions, project_id=normalized_project_id))
        if cursor is not None:
            ordered = [session for session in ordered if _session_is_after_cursor(session, cursor)]
        return _build_page(
            ordered,
            limit=normalized_limit,
            project_id=normalized_project_id,
        )


class SqliteMeasurementSessionRepository:
    """Durable local repository for offline-first measurement sessions.

    SQLite owns transactional durability. Chat 2 stores one versioned JSON payload per
    session so the local persistence format remains private to this slice and does not
    become a shared contract by accident. Query metadata is a private SQLite index
    surface derived from the validated payload and can be rebuilt without changing the
    payload schema.
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
        created_at_utc_us = _datetime_to_utc_microseconds(session.created_at)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO measurement_sessions(
                    session_id,
                    schema_version,
                    payload_json,
                    project_id,
                    created_at_utc_us
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json,
                    project_id = excluded.project_id,
                    created_at_utc_us = excluded.created_at_utc_us
                """,
                (
                    session.session_id,
                    _LOCAL_SCHEMA_VERSION,
                    payload,
                    session.project_id,
                    created_at_utc_us,
                ),
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
        return _decode_stored_session(session_id, schema_version, payload_json)

    def list_sessions(
        self, *, project_id: str | None = None
    ) -> tuple[MeasurementSession, ...]:
        sessions: list[MeasurementSession] = []
        cursor: MeasurementSessionPageCursor | None = None
        while True:
            page = self.list_session_page(
                project_id=project_id,
                limit=_MAX_PAGE_SIZE,
                cursor=cursor,
            )
            sessions.extend(page.sessions)
            if page.next_cursor is None:
                return tuple(sessions)
            cursor = page.next_cursor

    def list_session_page(
        self,
        *,
        project_id: str | None = None,
        limit: int = _DEFAULT_PAGE_SIZE,
        cursor: MeasurementSessionPageCursor | None = None,
    ) -> MeasurementSessionPage:
        normalized_project_id = _normalize_project_id(project_id)
        normalized_limit = _normalize_page_limit(limit)
        _validate_cursor_scope(cursor, normalized_project_id)

        where: list[str] = []
        parameters: list[Any] = []
        if normalized_project_id is not None:
            where.append("project_id = ?")
            parameters.append(normalized_project_id)
        if cursor is not None:
            cursor_us = _datetime_to_utc_microseconds(cursor.created_at)
            where.append(
                "(created_at_utc_us < ? OR "
                "(created_at_utc_us = ? AND session_id > ?))"
            )
            parameters.extend((cursor_us, cursor_us, cursor.session_id))

        query = (
            "SELECT session_id, schema_version, payload_json, project_id, created_at_utc_us "
            "FROM measurement_sessions"
        )
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at_utc_us DESC, session_id ASC LIMIT ?"
        parameters.append(normalized_limit + 1)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        decoded: list[MeasurementSession] = []
        for session_id, schema_version, payload_json, indexed_project_id, indexed_created_at in rows:
            session = _decode_stored_session(session_id, schema_version, payload_json)
            _validate_query_metadata(
                session,
                indexed_project_id=indexed_project_id,
                indexed_created_at_utc_us=indexed_created_at,
            )
            decoded.append(session)

        return _build_page(
            decoded,
            limit=normalized_limit,
            project_id=normalized_project_id,
        )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS measurement_sessions(
                    session_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    project_id TEXT,
                    created_at_utc_us INTEGER
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(measurement_sessions)")
            }
            if "project_id" not in columns:
                connection.execute(
                    "ALTER TABLE measurement_sessions ADD COLUMN project_id TEXT"
                )
            if "created_at_utc_us" not in columns:
                connection.execute(
                    "ALTER TABLE measurement_sessions ADD COLUMN created_at_utc_us INTEGER"
                )

            rows = connection.execute(
                """
                SELECT session_id, schema_version, payload_json
                FROM measurement_sessions
                WHERE project_id IS NULL OR created_at_utc_us IS NULL
                """
            ).fetchall()
            for session_id, schema_version, payload_json in rows:
                session = _decode_stored_session(session_id, schema_version, payload_json)
                connection.execute(
                    """
                    UPDATE measurement_sessions
                    SET project_id = ?, created_at_utc_us = ?
                    WHERE session_id = ?
                    """,
                    (
                        session.project_id,
                        _datetime_to_utc_microseconds(session.created_at),
                        session.session_id,
                    ),
                )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_measurement_sessions_order
                ON measurement_sessions(created_at_utc_us DESC, session_id ASC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_measurement_sessions_project_order
                ON measurement_sessions(project_id, created_at_utc_us DESC, session_id ASC)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5.0)


def _normalize_project_id(project_id: str | None) -> str | None:
    if project_id is None:
        return None
    normalized = project_id.strip()
    if not normalized:
        raise ValueError("project_id filter must not be empty")
    return normalized


def _normalize_page_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("session page limit must be an integer")
    if not 1 <= limit <= _MAX_PAGE_SIZE:
        raise ValueError(f"session page limit must be within [1, {_MAX_PAGE_SIZE}]")
    return limit


def _validate_cursor_scope(
    cursor: MeasurementSessionPageCursor | None, project_id: str | None
) -> None:
    if cursor is not None and cursor.project_id != project_id:
        raise ValueError("session page cursor project scope does not match request")


def _filter_and_sort_sessions(
    sessions: list[MeasurementSession], *, project_id: str | None
) -> tuple[MeasurementSession, ...]:
    if project_id is not None:
        sessions = [session for session in sessions if session.project_id == project_id]
    sessions.sort(key=lambda session: session.session_id)
    sessions.sort(key=lambda session: _datetime_to_utc_microseconds(session.created_at), reverse=True)
    return tuple(sessions)


def _session_is_after_cursor(
    session: MeasurementSession, cursor: MeasurementSessionPageCursor
) -> bool:
    session_us = _datetime_to_utc_microseconds(session.created_at)
    cursor_us = _datetime_to_utc_microseconds(cursor.created_at)
    return session_us < cursor_us or (
        session_us == cursor_us and session.session_id > cursor.session_id
    )


def _build_page(
    ordered_sessions: list[MeasurementSession],
    *,
    limit: int,
    project_id: str | None,
) -> MeasurementSessionPage:
    has_more = len(ordered_sessions) > limit
    sessions = tuple(ordered_sessions[:limit])
    next_cursor = None
    if has_more and sessions:
        last = sessions[-1]
        next_cursor = MeasurementSessionPageCursor(
            created_at=last.created_at,
            session_id=last.session_id,
            project_id=project_id,
        )
    return MeasurementSessionPage(sessions=sessions, next_cursor=next_cursor)


def _validate_query_metadata(
    session: MeasurementSession,
    *,
    indexed_project_id: Any,
    indexed_created_at_utc_us: Any,
) -> None:
    if not isinstance(indexed_project_id, str) or indexed_project_id != session.project_id:
        raise ValueError(f"stored session query metadata mismatch: {session.session_id}")
    if isinstance(indexed_created_at_utc_us, bool) or not isinstance(indexed_created_at_utc_us, int):
        raise ValueError(f"stored session query metadata mismatch: {session.session_id}")
    if indexed_created_at_utc_us != _datetime_to_utc_microseconds(session.created_at):
        raise ValueError(f"stored session query metadata mismatch: {session.session_id}")


def _require_aware_datetime(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _datetime_to_utc_microseconds(value: datetime) -> int:
    _require_aware_datetime(value, "created_at")
    delta = value.astimezone(timezone.utc) - _EPOCH_UTC
    return ((delta.days * 86_400 + delta.seconds) * 1_000_000) + delta.microseconds


def _decode_stored_session(
    session_id: str, schema_version: str, payload_json: str
) -> MeasurementSession:
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


def _format_datetime(value: datetime, field_name: str) -> str:
    _require_aware_datetime(value, field_name)
    return value.isoformat()


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value)
    _require_aware_datetime(parsed, field_name)
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
