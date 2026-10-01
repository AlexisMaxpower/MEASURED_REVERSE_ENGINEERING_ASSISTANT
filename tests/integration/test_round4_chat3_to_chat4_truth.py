from __future__ import annotations

from dataclasses import replace

from mrea_geometry import (
    CanonicalGeometryInput,
    ConstraintCandidate,
    ConstraintResolver,
    ConstraintSatisfactionAnalyzer,
    GeometryPipeline,
    Line,
    Point2D,
    SketchPackageBuilder,
)
from mrea_cad_bridge import TestDoubleCadAdapter, execute_cad_transfer_v1


def _context() -> CanonicalGeometryInput:
    return CanonicalGeometryInput(
        project_id="P-R4-X34",
        part_id="PART-R4-X34",
        capture_package_id="CP-R4-X34",
        measurement_package_id="MP-R4-X34",
        view_id="VIEW-R4-X34",
        source_view_ids=("VIEW-R4-X34",),
        coordinate_system="MAT_XY_MM",
        measurements=(),
    )


def test_round4_residual_approved_constraint_reaches_cad_without_relation_invention() -> None:
    line = Line(
        "L-R4-H",
        Point2D(0.0, 0.0),
        Point2D(10.0, 0.0),
        source="VISION_DETECTED",
        confidence=0.99,
    )
    draft = GeometryPipeline().build((line,), ())
    resolution = ConstraintResolver().resolve(draft)

    assert resolution.issues == ()
    assert len(resolution.constraints) == 1
    assert resolution.constraints[0].kind == "HORIZONTAL"
    assert resolution.constraints[0].status == "INFERRED"

    sketch = SketchPackageBuilder().build(
        draft,
        _context(),
        sketch_package_id="SP-R4-X34-VERIFIED",
        constraint_resolution=resolution,
    )
    assert sketch["constraints"] == [
        {
            "constraint_id": resolution.constraints[0].constraint_id,
            "type": "HORIZONTAL",
            "entity_ids": ["L-R4-H"],
            "status": "INFERRED",
        }
    ]
    assert sketch["unresolved"] == []

    transfer = execute_cad_transfer_v1(
        sketch_package=sketch,
        adapter=TestDoubleCadAdapter(),
        cad_package_id="CAD-R4-X34-VERIFIED",
        report_id="CADV-R4-X34-VERIFIED",
    )

    assert tuple(transfer.mapped_sketch_package.constraints) == tuple(sketch["constraints"])
    assert tuple(transfer.mapped_sketch_package.unresolved) == ()
    assert transfer.cad_verification_report["overall_status"] == "VERIFIED"


def test_round4_low_confidence_residual_remains_explicit_unresolved_through_cad() -> None:
    line = Line(
        "L-R4-LOW",
        Point2D(0.0, 0.0),
        Point2D(10.0, 0.005),
        source="VISION_DETECTED",
        confidence=0.99,
    )
    draft = GeometryPipeline().build((line,), ())
    stale_candidate = ConstraintCandidate(
        "C-R4-LOW",
        "HORIZONTAL",
        (line.entity_id,),
        confidence=1.0,
    )
    draft = replace(draft, constraints=(stale_candidate,))
    resolution = ConstraintResolver(
        minimum_confidence=0.95,
        satisfaction_analyzer=ConstraintSatisfactionAnalyzer(angular_tolerance=0.001),
    ).resolve(draft)

    assert resolution.constraints == ()
    assert [item.code for item in resolution.issues] == [
        "CONSTRAINT_BELOW_PROMOTION_CONFIDENCE"
    ]

    sketch = SketchPackageBuilder().build(
        draft,
        _context(),
        sketch_package_id="SP-R4-X34-UNRESOLVED",
        constraint_resolution=resolution,
    )
    assert sketch["constraints"] == []
    assert [item["code"] for item in sketch["unresolved"]] == [
        "CONSTRAINT_BELOW_PROMOTION_CONFIDENCE"
    ]

    transfer = execute_cad_transfer_v1(
        sketch_package=sketch,
        adapter=TestDoubleCadAdapter(),
        cad_package_id="CAD-R4-X34-UNRESOLVED",
        report_id="CADV-R4-X34-UNRESOLVED",
    )

    assert tuple(transfer.mapped_sketch_package.constraints) == ()
    assert [item["code"] for item in transfer.mapped_sketch_package.unresolved] == [
        "CONSTRAINT_BELOW_PROMOTION_CONFIDENCE"
    ]
