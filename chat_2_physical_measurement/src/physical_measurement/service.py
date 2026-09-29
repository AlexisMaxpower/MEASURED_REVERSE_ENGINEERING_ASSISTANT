from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_CANDIDATE_SOURCES = {
    ProvenanceSource.MANUAL_MEASURED,
    ProvenanceSource.DEVICE_REPORTED,
    ProvenanceSource.OCR_MEASURED,
    ProvenanceSource.VOICE_REPORTED,
}


class MeasurementSessionService:
    """Application service for physical-measurement candidates and verification.

    Manual, voice, OCR and device-reported values can enter the session as
    candidates. None of them becomes verified without the explicit confirmation
    transition exposed by :meth:`confirm_measurement`.
    """

    def __init__(
        self,
        repository: InMemoryMeasurementSessionRepository,
        *,
        id_factory: Callable[[str], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory or (lambda prefix: f"{prefix}_{uuid4().hex}")
        self._clock = clock or _utc_now

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value

    def create_session(self, project_id: str) -> MeasurementSession:
        session = MeasurementSession(
            session_id=self._id_factory("MS"),
            project_id=project_id,
            created_at=self._now(),
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

    def add_candidate(
        self,
        *,
        session_id: str,
        measurement_type: MeasurementType,
        value: Decimal | int | float | str,
        source: ProvenanceSource,
        view_id: str,
        anchor_a: FeatureAnchor,
        anchor_b: FeatureAnchor,
        evidence_frame_id: str | None = None,
        uncertainty_mm: Decimal | int | float | str | None = None,
        instrument_type: str | None = None,
    ) -> PhysicalMeasurement:
        if source not in _CANDIDATE_SOURCES:
            raise ValueError(f"unsupported physical-measurement candidate source: {source.value}")

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
            source=source,
            view_id=view_id,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            instrument_type=instrument_type,
            confirmed=False,
            created_at=self._now(),
        )
        self._repository.save(session.append(measurement))
        return measurement

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
        return self.add_candidate(
            session_id=session_id,
            measurement_type=measurement_type,
            value=value,
            source=ProvenanceSource.MANUAL_MEASURED,
            view_id=view_id,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            uncertainty_mm=uncertainty_mm,
            instrument_type=instrument_type,
        )

    def add_reported_candidate(
        self,
        *,
        session_id: str,
        measurement_type: MeasurementType,
        value: Decimal | int | float | str,
        source: ProvenanceSource,
        view_id: str,
        anchor_a: FeatureAnchor,
        anchor_b: FeatureAnchor,
        evidence_frame_id: str | None = None,
        uncertainty_mm: Decimal | int | float | str | None = None,
        instrument_type: str | None = None,
    ) -> PhysicalMeasurement:
        if source not in {
            ProvenanceSource.DEVICE_REPORTED,
            ProvenanceSource.OCR_MEASURED,
            ProvenanceSource.VOICE_REPORTED,
        }:
            raise ValueError("reported candidate source must be device, OCR or voice")
        return self.add_candidate(
            session_id=session_id,
            measurement_type=measurement_type,
            value=value,
            source=source,
            view_id=view_id,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            uncertainty_mm=uncertainty_mm,
            instrument_type=instrument_type,
        )

    def confirm_measurement(
        self,
        *,
        session_id: str,
        measurement_id: str,
        explicit_user_confirmation: bool,
    ) -> PhysicalMeasurement:
        if not explicit_user_confirmation:
            raise ValueError("verification requires explicit user confirmation")

        session = self._repository.get(session_id)
        measurement = session.get(measurement_id)
        if measurement.is_verified:
            raise ValueError("measurement is already verified")
        confirmed = measurement.confirm_by_user(at=self._now())
        self._repository.save(session.replace_measurement(confirmed))
        return confirmed

    def confirm_manual_measurement(
        self,
        *,
        session_id: str,
        measurement_id: str,
        explicit_user_confirmation: bool,
    ) -> PhysicalMeasurement:
        """Backward-compatible Phase A confirmation entrypoint."""

        return self.confirm_measurement(
            session_id=session_id,
            measurement_id=measurement_id,
            explicit_user_confirmation=explicit_user_confirmation,
        )

    def reject_candidate(self, *, session_id: str, measurement_id: str) -> PhysicalMeasurement:
        session = self._repository.get(session_id)
        measurement = session.get(measurement_id)
        if measurement.is_verified:
            raise ValueError("verified measurement cannot be rejected as a candidate")
        self._repository.save(session.remove_measurement(measurement_id))
        return measurement

    def get_session(self, session_id: str) -> MeasurementSession:
        return self._repository.get(session_id)
