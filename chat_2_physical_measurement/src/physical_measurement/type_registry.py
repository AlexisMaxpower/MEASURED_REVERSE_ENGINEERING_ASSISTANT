from __future__ import annotations

from dataclasses import dataclass

from .models import MeasurementType


@dataclass(frozen=True, slots=True)
class MeasurementTypeSemantics:
    """Stable domain semantics for one physical measurement type."""

    unit: str


class MeasurementTypeRegistry:
    """Single source of truth for Chat 2 measurement-type semantics.

    Canonical v1 uses millimetres for length-like measurements and degrees for
    angular measurements. Keeping that rule here prevents application flows from
    silently hard-coding ``mm`` for every measurement type.
    """

    _SEMANTICS: dict[MeasurementType, MeasurementTypeSemantics] = {
        MeasurementType.LINEAR_EXTERNAL: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.LINEAR_INTERNAL: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.THICKNESS: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.DEPTH: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.DIAMETER_EXTERNAL: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.DIAMETER_INTERNAL: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.RADIUS: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.ANGLE: MeasurementTypeSemantics(unit="deg"),
        MeasurementType.CENTER_DISTANCE: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.SLOT_WIDTH: MeasurementTypeSemantics(unit="mm"),
        MeasurementType.SURFACE_DISTANCE: MeasurementTypeSemantics(unit="mm"),
    }

    def semantics_for(self, measurement_type: MeasurementType) -> MeasurementTypeSemantics:
        try:
            return self._SEMANTICS[measurement_type]
        except KeyError as exc:  # defensive if a future enum member is added without registry support
            raise ValueError(f"unsupported measurement type: {measurement_type!r}") from exc

    def unit_for(self, measurement_type: MeasurementType) -> str:
        return self.semantics_for(measurement_type).unit

    def validate_complete(self) -> None:
        """Fail closed if the enum and registry ever drift apart."""

        registered = set(self._SEMANTICS)
        declared = set(MeasurementType)
        if registered != declared:
            missing = sorted(item.value for item in declared - registered)
            extra = sorted(item.value for item in registered - declared)
            raise ValueError(
                f"measurement type registry mismatch: missing={missing}, extra={extra}"
            )
