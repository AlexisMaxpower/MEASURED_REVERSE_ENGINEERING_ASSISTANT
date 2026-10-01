from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .constraint_satisfaction import ConstraintSatisfaction


@dataclass(frozen=True, slots=True)
class ConstraintConfidence:
    """Deterministic confidence derived only from geometric satisfaction residual."""

    constraint_id: str
    residual: float
    tolerance: float
    residual_ratio: float
    confidence: float
    unit: str


class ConstraintConfidenceModel:
    """Convert residual quality into a bounded confidence contribution.

    Exact geometry scores 1.0. A relation exactly on the accepted tolerance boundary
    scores ``boundary_confidence``. Unsatisfied or non-finite relations score 0.0.

    The quadratic curve intentionally penalizes large residuals while keeping very
    small measurement/vision noise close to 1.0. This score is only one contribution;
    ConstraintResolver still takes the minimum with candidate and entity confidence.
    """

    def __init__(self, *, boundary_confidence: float = 0.5) -> None:
        if not 0.0 <= boundary_confidence <= 1.0:
            raise ValueError("boundary_confidence must be between 0 and 1")
        self.boundary_confidence = boundary_confidence

    def score(self, satisfaction: ConstraintSatisfaction) -> ConstraintConfidence:
        residual = float(satisfaction.residual)
        tolerance = float(satisfaction.tolerance)

        if (
            not satisfaction.satisfied
            or not isfinite(residual)
            or not isfinite(tolerance)
            or tolerance < 0.0
        ):
            ratio = float("inf")
            confidence = 0.0
        elif tolerance == 0.0:
            ratio = 0.0 if residual == 0.0 else float("inf")
            confidence = 1.0 if residual == 0.0 else 0.0
        else:
            ratio = min(1.0, max(0.0, residual / tolerance))
            confidence = 1.0 - (1.0 - self.boundary_confidence) * ratio * ratio

        return ConstraintConfidence(
            constraint_id=satisfaction.constraint_id,
            residual=residual,
            tolerance=tolerance,
            residual_ratio=ratio,
            confidence=confidence,
            unit=satisfaction.unit,
        )
