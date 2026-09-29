"""Deterministic geometry core and canonical v1 bridge owned by MREA Chat 3."""

from .constraints import ConstraintIssue, ConstraintResolution, ConstraintResolver, ResolvedConstraint
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
from .vision import CandidateIssue, GeometryExtractionResult, ImageGeometryExtractor
from .vision_pipeline import VisionGeometryPipeline

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
    "ConstraintIssue",
    "ConstraintResolution",
    "ConstraintResolver",
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
    "ResolvedConstraint",
    "SketchPackageBuilder",
    "UnresolvedBinding",
    "VisionGeometryPipeline",
]
