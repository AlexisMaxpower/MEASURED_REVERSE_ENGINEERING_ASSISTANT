"""Deterministic geometry core and canonical v1 bridge owned by MREA Chat 3."""

from .constraints import ConstraintIssue, ConstraintResolution, ConstraintResolver, ResolvedConstraint
from .contracts import CanonicalGeometryInput, CanonicalInputAdapter
from .dimensioned_view import DimensionedViewArtifact, DimensionedViewRenderer, ReferenceImageLayer
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
    "DimensionedViewArtifact",
    "DimensionedViewRenderer",
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
    "ReferenceImageLayer",
    "ResolvedConstraint",
    "SketchPackageBuilder",
    "UnresolvedBinding",
    "VisionGeometryPipeline",
]
