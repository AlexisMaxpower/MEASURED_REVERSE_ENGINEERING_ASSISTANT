from __future__ import annotations

from mrea_geometry import (
    Circle,
    ConstraintResolution,
    ConstraintSystemAnalyzer,
    GeometryPipeline,
    Line,
    Point2D,
    ResolvedConstraint,
)


def _horizontal(entity_id: str, y: float) -> Line:
    return Line(entity_id, Point2D(0.0, y), Point2D(10.0, y))


def _vertical(entity_id: str, x: float) -> Line:
    return Line(entity_id, Point2D(x, 0.0), Point2D(x, 10.0))


def _draft(*entities):
    return GeometryPipeline().build(tuple(entities), ())


def _constraint(constraint_id: str, kind: str, *entity_ids: str) -> ResolvedConstraint:
    return ResolvedConstraint(
        constraint_id=constraint_id,
        kind=kind,
        entity_ids=tuple(entity_ids),
        status="INFERRED",
        confidence=1.0,
    )


def _resolution(*constraints: ResolvedConstraint) -> ConstraintResolution:
    return ConstraintResolution(constraints=tuple(constraints), issues=())


def test_consistent_system_reports_no_supported_global_issue() -> None:
    draft = _draft(_horizontal("L1", 0.0), _vertical("L2", 20.0))
    resolution = _resolution(
        _constraint("C-H", "HORIZONTAL", "L1"),
        _constraint("C-V", "VERTICAL", "L2"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONSISTENT"
    assert diagnosis.issues == ()
    assert diagnosis.redundant_constraint_ids == ()
    assert diagnosis.conflicting_constraint_ids == ()


def test_same_line_horizontal_and_vertical_is_global_orientation_conflict() -> None:
    draft = _draft(_horizontal("L1", 0.0))
    resolution = _resolution(
        _constraint("A-H", "HORIZONTAL", "L1"),
        _constraint("B-V", "VERTICAL", "L1"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("A-H", "B-V")
    assert [item.code for item in diagnosis.issues] == [
        "CONSTRAINT_SYSTEM_CONFLICTING_ORIENTATION"
    ]
    assert diagnosis.issues[0].constraint_ids == ("A-H", "B-V")
    assert diagnosis.issues[0].entity_ids == ("L1",)


def test_parallel_and_perpendicular_same_pair_is_orientation_conflict() -> None:
    draft = _draft(_horizontal("L1", 0.0), _horizontal("L2", 5.0))
    resolution = _resolution(
        _constraint("A-P", "PARALLEL", "L1", "L2"),
        _constraint("B-X", "PERPENDICULAR", "L2", "L1"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("A-P", "B-X")
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_CONFLICTING_ORIENTATION"


def test_transitive_orientation_cycle_detects_conflict() -> None:
    draft = _draft(
        _horizontal("L1", 0.0),
        _horizontal("L2", 5.0),
        _horizontal("L3", 10.0),
    )
    resolution = _resolution(
        _constraint("A-P12", "PARALLEL", "L1", "L2"),
        _constraint("B-P23", "PARALLEL", "L2", "L3"),
        _constraint("C-X13", "PERPENDICULAR", "L1", "L3"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("A-P12", "B-P23", "C-X13")
    issue = diagnosis.issues[0]
    assert issue.code == "CONSTRAINT_SYSTEM_CONFLICTING_ORIENTATION"
    assert issue.constraint_ids == ("A-P12", "B-P23", "C-X13")
    assert issue.entity_ids == ("L1", "L2", "L3")


def test_axis_constraints_make_parallel_relation_redundant() -> None:
    draft = _draft(_horizontal("L1", 0.0), _horizontal("L2", 5.0))
    resolution = _resolution(
        _constraint("A-H1", "HORIZONTAL", "L1"),
        _constraint("B-H2", "HORIZONTAL", "L2"),
        _constraint("C-P", "PARALLEL", "L1", "L2"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("C-P",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_ORIENTATION"
    assert diagnosis.issues[0].constraint_ids == ("A-H1", "B-H2", "C-P")


def test_axis_constraints_make_perpendicular_relation_redundant() -> None:
    draft = _draft(_horizontal("L1", 0.0), _vertical("L2", 20.0))
    resolution = _resolution(
        _constraint("A-H", "HORIZONTAL", "L1"),
        _constraint("B-V", "VERTICAL", "L2"),
        _constraint("C-X", "PERPENDICULAR", "L1", "L2"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("C-X",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_ORIENTATION"


def test_parallel_transitive_cycle_marks_only_closing_relation_redundant() -> None:
    draft = _draft(
        _horizontal("L1", 0.0),
        _horizontal("L2", 5.0),
        _horizontal("L3", 10.0),
    )
    resolution = _resolution(
        _constraint("A-P12", "PARALLEL", "L1", "L2"),
        _constraint("B-P23", "PARALLEL", "L2", "L3"),
        _constraint("C-P13", "PARALLEL", "L1", "L3"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("C-P13",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_ORIENTATION"
    assert diagnosis.issues[0].constraint_ids == ("A-P12", "B-P23", "C-P13")


def test_equal_transitive_cycle_is_redundant_without_geometry_mutation() -> None:
    draft = _draft(
        _horizontal("L1", 0.0),
        _horizontal("L2", 5.0),
        _horizontal("L3", 10.0),
    )
    resolution = _resolution(
        _constraint("A-E12", "EQUAL", "L1", "L2"),
        _constraint("B-E23", "EQUAL", "L2", "L3"),
        _constraint("C-E13", "EQUAL", "L1", "L3"),
    )
    original_entities = draft.entities
    original_constraints = resolution.constraints

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("C-E13",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_CYCLE"
    assert diagnosis.issues[0].constraint_ids == ("A-E12", "B-E23", "C-E13")
    assert draft.entities == original_entities
    assert resolution.constraints == original_constraints


def test_concentric_transitive_cycle_is_redundant() -> None:
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 3.0),
        Circle("C2", Point2D(0.0, 0.0), 4.0),
        Circle("C3", Point2D(0.0, 0.0), 5.0),
    )
    draft = _draft(*circles)
    resolution = _resolution(
        _constraint("A-C12", "CONCENTRIC", "C1", "C2"),
        _constraint("B-C23", "CONCENTRIC", "C2", "C3"),
        _constraint("C-C13", "CONCENTRIC", "C1", "C3"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("C-C13",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_CYCLE"


def test_transitive_concentric_relation_conflicts_with_round_tangency() -> None:
    circles = (
        Circle("C1", Point2D(0.0, 0.0), 3.0),
        Circle("C2", Point2D(0.0, 0.0), 4.0),
        Circle("C3", Point2D(0.0, 0.0), 5.0),
    )
    draft = _draft(*circles)
    resolution = _resolution(
        _constraint("A-C12", "CONCENTRIC", "C1", "C2"),
        _constraint("B-C23", "CONCENTRIC", "C2", "C3"),
        _constraint("C-T13", "TANGENT", "C1", "C3"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("A-C12", "B-C23", "C-T13")
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_CONFLICTING_ROUND_RELATION"
    assert diagnosis.issues[0].constraint_ids == ("A-C12", "B-C23", "C-T13")
    assert diagnosis.issues[0].entity_ids == ("C1", "C2", "C3")


def test_semantic_duplicate_uses_normalized_pair_order() -> None:
    draft = _draft(_horizontal("L1", 0.0), _horizontal("L2", 5.0))
    resolution = _resolution(
        _constraint("A-EQ", "EQUAL", "L1", "L2"),
        _constraint("B-EQ", "EQUAL", "L2", "L1"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "REDUNDANT"
    assert diagnosis.redundant_constraint_ids == ("B-EQ",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_REDUNDANT_DUPLICATE"
    assert diagnosis.issues[0].constraint_ids == ("A-EQ", "B-EQ")
    assert diagnosis.issues[0].entity_ids == ("L1", "L2")


def test_missing_entity_reference_fails_closed() -> None:
    draft = _draft(_horizontal("L1", 0.0))
    resolution = _resolution(_constraint("C-MISSING", "HORIZONTAL", "L-NOPE"))

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("C-MISSING",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_ENTITY_MISSING"
    assert diagnosis.issues[0].entity_ids == ("L-NOPE",)


def test_duplicate_constraint_id_fails_closed_without_guessing_identity() -> None:
    draft = _draft(_horizontal("L1", 0.0), _vertical("L2", 20.0))
    resolution = _resolution(
        _constraint("C-DUP", "HORIZONTAL", "L1"),
        _constraint("C-DUP", "VERTICAL", "L2"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONFLICTING"
    assert diagnosis.conflicting_constraint_ids == ("C-DUP",)
    assert diagnosis.issues[0].code == "CONSTRAINT_SYSTEM_DUPLICATE_CONSTRAINT_ID"


def test_coincident_triangle_is_not_treated_as_transitive_redundancy() -> None:
    draft = _draft(
        _horizontal("L1", 0.0),
        _horizontal("L2", 5.0),
        _horizontal("L3", 10.0),
    )
    resolution = _resolution(
        _constraint("A-C12", "COINCIDENT", "L1", "L2"),
        _constraint("B-C23", "COINCIDENT", "L2", "L3"),
        _constraint("C-C13", "COINCIDENT", "L1", "L3"),
    )

    diagnosis = ConstraintSystemAnalyzer().analyze(draft, resolution)

    assert diagnosis.status == "CONSISTENT"
    assert diagnosis.issues == ()


def test_diagnosis_is_deterministic_for_reversed_constraint_order() -> None:
    draft = _draft(
        _horizontal("L1", 0.0),
        _horizontal("L2", 5.0),
        _horizontal("L3", 10.0),
    )
    constraints = (
        _constraint("A-P12", "PARALLEL", "L1", "L2"),
        _constraint("B-P23", "PARALLEL", "L2", "L3"),
        _constraint("C-X13", "PERPENDICULAR", "L1", "L3"),
    )
    analyzer = ConstraintSystemAnalyzer()

    forward = analyzer.analyze(draft, _resolution(*constraints))
    reverse = analyzer.analyze(draft, _resolution(*reversed(constraints)))

    assert forward == reverse
