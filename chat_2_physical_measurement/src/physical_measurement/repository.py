from __future__ import annotations

from copy import deepcopy

from .models import MeasurementSession


class InMemoryMeasurementSessionRepository:
    """Phase A persistence boundary used until project persistence is integrated."""

    def __init__(self) -> None:
        self._sessions: dict[str, MeasurementSession] = {}

    def save(self, session: MeasurementSession) -> None:
        self._sessions[session.session_id] = deepcopy(session)

    def get(self, session_id: str) -> MeasurementSession:
        try:
            return deepcopy(self._sessions[session_id])
        except KeyError as exc:
            raise KeyError(f"measurement session not found: {session_id}") from exc
