"""Internal deterministic geometry core owned by MREA Chat 3.

It intentionally does not define or serialize canonical shared contracts.
"""

from .core import (
    AnchorEntityMatcher,
    ConstraintCandidateEngine,
    DimensionBinder,
    GeometryConflictDetector,
    GeometryPipeline,
)
from .graph import GeometryGraph
from .models import (
    AnchorRef,
    Arc,
    Circle,
    ConstraintCandidate,
    DimensionBinding,
    GeometryConflict,
    GeometryDraft,
    Line,
    MeasurementRef,
    Point2D,
    UnresolvedBinding,
)

__all__ = [
    "AnchorEntityMatcher",
    "AnchorRef",
    "Arc",
    "Circle",
    "ConstraintCandidate",
    "ConstraintCandidateEngine",
    "DimensionBinder",
    "DimensionBinding",
    "GeometryConflict",
    "GeometryConflictDetector",
    "GeometryDraft",
    "GeometryGraph",
    "GeometryPipeline",
    "Line",
    "MeasurementRef",
    "Point2D",
    "UnresolvedBinding",
]
