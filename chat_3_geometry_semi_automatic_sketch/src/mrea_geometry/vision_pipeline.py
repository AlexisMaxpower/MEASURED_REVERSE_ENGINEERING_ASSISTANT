from __future__ import annotations

from .constraint_system import ConstraintSystemAnalyzer
from .constraints import ConstraintResolver
from .contracts import CanonicalGeometryInput
from .core import GeometryPipeline
from .sketch_package import SketchPackageBuilder
from .vision import GeometryExtractionResult


class VisionGeometryPipeline:
    """Constraint-aware image-candidate -> canonical sketch composition."""

    def __init__(
        self,
        *,
        geometry: GeometryPipeline | None = None,
        constraint_resolver: ConstraintResolver | None = None,
        constraint_system_analyzer: ConstraintSystemAnalyzer | None = None,
        builder: SketchPackageBuilder | None = None,
    ) -> None:
        self.geometry = geometry or GeometryPipeline()
        self.constraint_resolver = constraint_resolver or ConstraintResolver()
        self.constraint_system_analyzer = constraint_system_analyzer or ConstraintSystemAnalyzer()
        self.builder = builder or SketchPackageBuilder()

    def build_sketch(
        self,
        extraction: GeometryExtractionResult,
        context: CanonicalGeometryInput,
        *,
        sketch_package_id: str,
    ) -> dict:
        draft = self.geometry.build(extraction.primitives, context.measurements)
        resolution = self.constraint_resolver.resolve(draft)
        system_analysis = self.constraint_system_analyzer.analyze(resolution)
        package = self.builder.build(
            draft,
            context,
            sketch_package_id=sketch_package_id,
            constraint_resolution=system_analysis.resolution,
        )
        package["unresolved"].extend(
            issue.to_dict()
            for issue in sorted(extraction.issues, key=lambda item: item.issue_id)
        )
        package["unresolved"].sort(key=lambda item: item["unresolved_id"])
        return package
