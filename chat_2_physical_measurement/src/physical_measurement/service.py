from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

from .models import (
    FeatureAnchor,
    MeasurementSession,
    MeasurementType,
    PhysicalMeasurement,
    ProvenanceSource,
    decimal_value,
)
from .repository import InMemoryMeasurementSessionRepository


class MeasurementSessionService:
    """Application service for Phase A: manual anchors + manual value + confirmation."""

    def __init__(
        self,
        repository: InMemoryMeasurementSessionRepository,
        *,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory or (lambda prefix: f"{prefix}_{uuid4().hex}")

    def create_session(self, project_id: str) -> MeasurementSession:
        session = MeasurementSession(
            session_id=self._id_factory("MS"),
            project_id=project_id,
        )
        self._repository.save(session)
        return session

    def create_manual_anchor(
        self,
        *,
        view_id: str,
        reference_frame_id: str,
        x_px: float,
        y_px: float,
    ) -> FeatureAnchor:
        return FeatureAnchor(
            anchor_id=self._id_factory("A"),
            view_id=view_id,
            reference_frame_id=reference_frame_id,
            x_px=x_px,
            y_px=y_px,
        )

    def add_manual_candidate(
        self,
        *,
        session_id: str,
        measurement_type: MeasurementType,
        value: Decimal | int | float | str,
        view_id: str,
        anchor_a: FeatureAnchor,
        anchor_b: FeatureAnchor,
        evidence_frame_id: str | None = None,
        uncertainty_mm: Decimal | int | float | str | None = None,
        instrument_type: str | None = None,
    ) -> PhysicalMeasurement:
        session = self._repository.get(session_id)
        measurement = PhysicalMeasurement(
            measurement_id=self._id_factory("M"),
            measurement_type=measurement_type,
            value=decimal_value(value),
            unit="mm",
            uncertainty_mm=(
                decimal_value(uncertainty_mm, "uncertainty_mm")
                if uncertainty_mm is not None
                else None
            ),
            source=ProvenanceSource.MANUAL_MEASURED,
            view_id=view_id,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            instrument_type=instrument_type,
            confirmed=False,
        )
        self._repository.save(session.append(measurement))
        return measurement

    def confirm_manual_measurement(
        self,
        *,
        session_id: str,
        measurement_id: str,
        explicit_user_confirmation: bool,
    ) -> PhysicalMeasurement:
        if not explicit_user_confirmation:
            raise ValueError("verification requires explicit user confirmation in Phase A")

        session = self._repository.get(session_id)
        measurement = session.get(measurement_id)
        confirmed = measurement.confirm_by_user()
        self._repository.save(session.replace_measurement(confirmed))
        return confirmed

    def get_session(self, session_id: str) -> MeasurementSession:
        return self._repository.get(session_id)
