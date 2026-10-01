from __future__ import annotations

from math import isfinite

from .core import GeometryConflictDetector
from .models import DimensionBinding, GeometryConflict


class UncertaintyAwareGeometryConflictDetector(GeometryConflictDetector):
    """Conflict policy that respects explicit physical measurement uncertainty.

    The canonical measured value remains authoritative. Uncertainty only widens the
    comparison tolerance used to decide whether derived geometry should be reported
    as conflicting with that verified measurement.
    """

    def __init__(
        self,
        *,
        tolerance: float = 0.05,
        uncertainty_scale: float = 1.0,
    ) -> None:
        if not isfinite(tolerance) or tolerance < 0:
            raise ValueError("tolerance must be a finite non-negative number")
        if not isfinite(uncertainty_scale) or uncertainty_scale < 0:
            raise ValueError("uncertainty_scale must be a finite non-negative number")
        super().__init__(tolerance=tolerance)
        self.uncertainty_scale = float(uncertainty_scale)

    def effective_tolerance(self, dimension: DimensionBinding) -> float:
        uncertainty = dimension.uncertainty
        if uncertainty is None:
            return self.tolerance
        if not isfinite(uncertainty) or uncertainty < 0:
            raise ValueError("dimension uncertainty must be a finite non-negative number")
        return self.tolerance + self.uncertainty_scale * uncertainty

    def detect(
        self,
        dimensions: tuple[DimensionBinding, ...],
    ) -> tuple[GeometryConflict, ...]:
        result: list[GeometryConflict] = []
        for dimension in dimensions:
            if not dimension.verified or dimension.geometry_estimate is None:
                continue

            effective_tolerance = self.effective_tolerance(dimension)
            delta = abs(dimension.value - dimension.geometry_estimate)
            if delta > effective_tolerance:
                result.append(
                    GeometryConflict(
                        conflict_id=f"GC_{dimension.measurement_id}",
                        code="VERIFIED_MEASUREMENT_VS_DERIVED_GEOMETRY",
                        measurement_id=dimension.measurement_id,
                        measured_value=dimension.value,
                        derived_value=dimension.geometry_estimate,
                        delta=delta,
                        tolerance=effective_tolerance,
                    )
                )
        return tuple(result)
