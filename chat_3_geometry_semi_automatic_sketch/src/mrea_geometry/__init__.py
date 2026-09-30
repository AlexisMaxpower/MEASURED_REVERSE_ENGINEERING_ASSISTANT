"""Deterministic geometry core and canonical v1 bridge owned by MREA Chat 3."""

from .contracts import CanonicalGeometryInput, CanonicalInputAdapter
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
    PointEntity,
    UnresolvedBinding,
)
from .sketch_package import SketchPackageBuilder
from .vision import CandidateIssue, GeometryExtractionResult, ImageGeometryExtractor, VisionGeometryPipeline

__all__ = [
    "AnchorEntityMatcher",
    "AnchorRef",
    "Arc",
    "CanonicalGeometryInput",
    "CanonicalInputAdapter",
    "CandidateIssue",
    "Circle",
    "ConstraintCandidate",
    "ConstraintCandidateEngine",
    "DimensionBinder",
    "DimensionBinding",
    "GeometryConflict",
    "GeometryConflictDetector",
    "GeometryDraft",
    "GeometryGraph",
    "GeometryExtractionResult",
    "GeometryPipeline",
    "ImageGeometryExtractor",
    "Line",
    "MeasurementRef",
    "Point2D",
    "PointEntity",
    "SketchPackageBuilder",
    "UnresolvedBinding",
    "VisionGeometryPipeline",
]
