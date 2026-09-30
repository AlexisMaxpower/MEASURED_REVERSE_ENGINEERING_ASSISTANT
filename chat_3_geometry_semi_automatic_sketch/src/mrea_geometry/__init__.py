"""Deterministic geometry core and canonical v1 bridge owned by MREA Chat 3."""

from .constraint_confidence import ConstraintConfidence, ConstraintConfidenceModel
from .constraint_satisfaction import ConstraintSatisfaction, ConstraintSatisfactionAnalyzer
from .constraint_system import ConstraintSystemAnalysis, ConstraintSystemAnalyzer
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
    "ConstraintConfidence",
    "ConstraintConfidenceModel",
    "ConstraintIssue",
    "ConstraintResolution",
    "ConstraintResolver",
    "ConstraintSatisfaction",
    "ConstraintSatisfactionAnalyzer",
    "ConstraintSystemAnalysis",
    "ConstraintSystemAnalyzer",
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
