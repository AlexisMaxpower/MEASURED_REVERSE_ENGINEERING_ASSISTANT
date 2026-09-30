from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Iterable


class MeasurementType(StrEnum):
    LINEAR_EXTERNAL = "LINEAR_EXTERNAL"
    LINEAR_INTERNAL = "LINEAR_INTERNAL"
    THICKNESS = "THICKNESS"
    DEPTH = "DEPTH"
    DIAMETER_EXTERNAL = "DIAMETER_EXTERNAL"
    DIAMETER_INTERNAL = "DIAMETER_INTERNAL"
    RADIUS = "RADIUS"
    ANGLE = "ANGLE"
    CENTER_DISTANCE = "CENTER_DISTANCE"
    SLOT_WIDTH = "SLOT_WIDTH"
    SURFACE_DISTANCE = "SURFACE_DISTANCE"


class ProvenanceSource(StrEnum):
    MANUAL_MEASURED = "MANUAL_MEASURED"
    DEVICE_REPORTED = "DEVICE_REPORTED"
    OCR_MEASURED = "OCR_MEASURED"
    VOICE_REPORTED = "VOICE_REPORTED"
    VISION_DETECTED = "VISION_DETECTED"
    CALIBRATION_DERIVED = "CALIBRATION_DERIVED"
    GEOMETRY_DERIVED = "GEOMETRY_DERIVED"
    AI_INFERRED = "AI_INFERRED"
    USER_CONFIRMED = "USER_CONFIRMED"


def _non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def decimal_value(value: Decimal | int | float | str, field_name: str = "value") -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class FeatureAnchor:
    """Point selected on a reference frame, optionally linked to a detected feature."""

    anchor_id: str
    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float
    feature_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor_id", _non_empty(self.anchor_id, "anchor_id"))
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(
            self,
            "reference_frame_id",
            _non_empty(self.reference_frame_id, "reference_frame_id"),
        )
        if self.feature_id is not None:
            object.__setattr__(self, "feature_id", _non_empty(self.feature_id, "feature_id"))
        if self.x_px < 0 or self.y_px < 0:
            raise ValueError("anchor pixel coordinates must be >= 0")

    def snap_to(self, *, feature_id: str, x_px: float, y_px: float) -> "FeatureAnchor":
        return replace(
            self,
            feature_id=feature_id,
            x_px=x_px,
            y_px=y_px,
        )


@dataclass(frozen=True, slots=True)
class PhysicalMeasurement:
    """Internal physical measurement aligned with canonical 1..3 anchor cardinality."""

    measurement_id: str
    measurement_type: MeasurementType
    value: Decimal
    unit: str
    source: ProvenanceSource
    view_id: str
    anchor_a: FeatureAnchor
    anchor_b: FeatureAnchor | None = None
    anchor_c: FeatureAnchor | None = None
    evidence_frame_id: str | None = None
    uncertainty: Decimal | None = None
    uncertainty_mm: Decimal | None = None
    instrument_type: str | None = None
    confirmed: bool = False
    confirmed_at: datetime | None = None
    confirmation_source: ProvenanceSource | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurement_id", _non_empty(self.measurement_id, "measurement_id"))
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(self, "unit", _non_empty(self.unit, "unit"))
        object.__setattr__(self, "value", decimal_value(self.value))

        neutral_uncertainty = (
            decimal_value(self.uncertainty, "uncertainty")
            if self.uncertainty is not None
            else None
        )
        legacy_uncertainty = (
            decimal_value(self.uncertainty_mm, "uncertainty_mm")
            if self.uncertainty_mm is not None
            else None
        )
        for field_name, candidate in (
            ("uncertainty", neutral_uncertainty),
            ("uncertainty_mm", legacy_uncertainty),
        ):
            if candidate is not None and candidate < 0:
                raise ValueError(f"{field_name} must be >= 0")

        if legacy_uncertainty is not None and self.unit != "mm":
            raise ValueError("uncertainty_mm compatibility input is only valid for mm measurements")
        if (
            neutral_uncertainty is not None
            and legacy_uncertainty is not None
            and neutral_uncertainty != legacy_uncertainty
        ):
            raise ValueError("uncertainty and uncertainty_mm must match when both are supplied")

        resolved_uncertainty = (
            neutral_uncertainty if neutral_uncertainty is not None else legacy_uncertainty
        )
        object.__setattr__(self, "uncertainty", resolved_uncertainty)
        object.__setattr__(
            self,
            "uncertainty_mm",
            resolved_uncertainty if self.unit == "mm" else None,
        )

        if self.anchor_c is not None and self.anchor_b is None:
            raise ValueError("anchor_c requires anchor_b so anchor order remains contiguous")

        anchors = self.anchors
        anchor_ids = [anchor.anchor_id for anchor in anchors]
        if len(anchor_ids) != len(set(anchor_ids)):
            raise ValueError("measurement anchors must be unique")
        for anchor in anchors:
            if anchor.view_id != self.view_id:
                raise ValueError("measurement view_id must match all anchors")
        reference_frame_ids = {anchor.reference_frame_id for anchor in anchors}
        if len(reference_frame_ids) != 1:
            raise ValueError("all anchors must use the same reference frame")

        candidate_sources = {
            ProvenanceSource.MANUAL_MEASURED,
            ProvenanceSource.DEVICE_REPORTED,
            ProvenanceSource.OCR_MEASURED,
            ProvenanceSource.VOICE_REPORTED,
        }
        if self.source not in candidate_sources:
            raise ValueError(
                "physical measurement candidates require a direct measurement/report source"
            )
        if self.confirmed and self.confirmation_source is None:
            raise ValueError("confirmed measurement requires confirmation_source")
        if not self.confirmed and self.confirmed_at is not None:
            raise ValueError("unconfirmed measurement cannot have confirmed_at")

    @property
    def anchors(self) -> tuple[FeatureAnchor, ...]:
        return tuple(
            anchor
            for anchor in (self.anchor_a, self.anchor_b, self.anchor_c)
            if anchor is not None
        )

    @property
    def is_verified(self) -> bool:
        return self.confirmed

    def replace_anchor(self, updated: FeatureAnchor) -> "PhysicalMeasurement":
        if updated.anchor_id == self.anchor_a.anchor_id:
            return replace(self, anchor_a=updated)
        if self.anchor_b is not None and updated.anchor_id == self.anchor_b.anchor_id:
            return replace(self, anchor_b=updated)
        if self.anchor_c is not None and updated.anchor_id == self.anchor_c.anchor_id:
            return replace(self, anchor_c=updated)
        raise KeyError(updated.anchor_id)

    def confirm_by_user(self, *, at: datetime | None = None) -> "PhysicalMeasurement":
        return replace(
            self,
            confirmed=True,
            confirmed_at=at or datetime.now(timezone.utc),
            confirmation_source=ProvenanceSource.USER_CONFIRMED,
        )


@dataclass(frozen=True, slots=True)
class MeasurementSession:
    session_id: str
    project_id: str
    measurements: tuple[PhysicalMeasurement, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _non_empty(self.session_id, "session_id"))
        object.__setattr__(self, "project_id", _non_empty(self.project_id, "project_id"))
        ids = [measurement.measurement_id for measurement in self.measurements]
        if len(ids) != len(set(ids)):
            raise ValueError("measurement ids must be unique within a session")

    def append(self, measurement: PhysicalMeasurement) -> "MeasurementSession":
        if any(item.measurement_id == measurement.measurement_id for item in self.measurements):
            raise ValueError(f"duplicate measurement_id: {measurement.measurement_id}")
        return replace(self, measurements=(*self.measurements, measurement))

    def replace_measurement(self, updated: PhysicalMeasurement) -> "MeasurementSession":
        found = False
        values: list[PhysicalMeasurement] = []
        for item in self.measurements:
            if item.measurement_id == updated.measurement_id:
                values.append(updated)
                found = True
            else:
                values.append(item)
        if not found:
            raise KeyError(updated.measurement_id)
        return replace(self, measurements=tuple(values))

    def remove_measurement(self, measurement_id: str) -> "MeasurementSession":
        values = tuple(
            item for item in self.measurements if item.measurement_id != measurement_id
        )
        if len(values) == len(self.measurements):
            raise KeyError(measurement_id)
        return replace(self, measurements=values)

    def get(self, measurement_id: str) -> PhysicalMeasurement:
        for item in self.measurements:
            if item.measurement_id == measurement_id:
                return item
        raise KeyError(measurement_id)

    def verified(self) -> Iterable[PhysicalMeasurement]:
        return (item for item in self.measurements if item.is_verified)
