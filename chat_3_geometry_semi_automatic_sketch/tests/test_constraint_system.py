from __future__ import annotations

from mrea_geometry import (
    ConstraintIssue,
    ConstraintResolution,
    ConstraintSystemAnalyzer,
    ResolvedConstraint,
)


def _constraint(
    constraint_id: str,
    kind: str,
    entity_ids: tuple[str, ...],
    *,
    confidence: float = 1.0,
    status: str = "INFERRED",
) -> ResolvedConstraint:
    return ResolvedConstraint(
        constraint_id=constraint_id,
        kind=kind,
        entity_ids=entity_ids,
        status=status,  # type: ignore[arg-type]
        confidence=confidence,
    )


def _resolution(*constraints: ResolvedConstraint) -> ConstraintResolution:
    return ConstraintResolution(constraints=tuple(constraints), issues=())


def test_consistent_orientation_chain_keeps_minimal_independent_set() -> None:
    analysis = ConstraintSystemAnalyzer().analyze(
        _resolution(
            _constraint("C-H-A", "HORIZONTAL", ("A",)),
            _constraint("C-V-C", "VERTICAL", ("C",)),
            _constraint("C-P-AB", "PARALLEL", ("A", "B")),
            _constraint("C-PP-BC", "PERPENDICULAR", ("B", "C")),
        )
    )

    assert [item.constraint_id for item in analysis.resolution.constraints] == [
        "C-H-A",
        "C-P-AB",
        "C-V-C",
    ]
    assert analysis.redundant_constraint_ids == ("C-PP-BC",)
    assert analysis.rejected_constraint_ids == ()
    assert analysis.resolution.issues == ()


def test_conflicting_orientation_relation_is_rejected_fail_closed() -> None:
    analysis = ConstraintSystemAnalyzer().analyze(
        _resolution(
            _constraint("C-H-A", "HORIZONTAL", ("A",)),
            _constraint("C-H-B", "HORIZONTAL", ("B",)),
            _constraint(
                "C-PP-AB",
                "PERPENDICULAR",
                ("A", "B"),
                confidence=0.9,
            ),
        )
    )

    assert [item.constraint_id for item in analysis.resolution.constraints] == [
        "C-H-A",
        "C-H-B",
    ]
    assert analysis.rejected_constraint_ids == ("C-PP-AB",)
    assert [item.code for item in analysis.resolution.issues] == [
        "OVERCONSTRAINED_ORIENTATION_CONFLICT"
    ]
    assert analysis.resolution.issues[0].entity_ids == ("A", "B")


def test_detected_relation_wins_over_inferred_relation_at_equal_confidence() -> None:
    analysis = ConstraintSystemAnalyzer().analyze(
        _resolution(
            _constraint("C-H-A", "HORIZONTAL", ("A",), status="INFERRED"),
            _constraint("C-V-A", "VERTICAL", ("A",), status="DETECTED"),
        )
    )

    assert [item.constraint_id for item in analysis.resolution.constraints] == ["C-V-A"]
    assert analysis.rejected_constraint_ids == ("C-H-A",)
    assert analysis.resolution.issues[0].code == "OVERCONSTRAINED_ORIENTATION_CONFLICT"


def test_parallel_cycle_drops_only_transitive_redundancy() -> None:
    analysis = ConstraintSystemAnalyzer().analyze(
        _resolution(
            _constraint("C1-P-AB", "PARALLEL", ("A", "B")),
            _constraint("C2-P-BC", "PARALLEL", ("B", "C")),
            _constraint("C3-P-AC", "PARALLEL", ("A", "C")),
        )
    )

    assert [item.constraint_id for item in analysis.resolution.constraints] == [
        "C1-P-AB",
        "C2-P-BC",
    ]
    assert analysis.redundant_constraint_ids == ("C3-P-AC",)
    assert analysis.rejected_constraint_ids == ()


def test_equal_cycle_drops_only_transitive_redundancy() -> None:
    analysis = ConstraintSystemAnalyzer().analyze(
        _resolution(
            _constraint("C1-E-AB", "EQUAL", ("A", "B")),
            _constraint("C2-E-BC", "EQUAL", ("B", "C")),
            _constraint("C3-E-AC", "EQUAL", ("A", "C")),
        )
    )

    assert [item.constraint_id for item in analysis.resolution.constraints] == [
        "C1-E-AB",
        "C2-E-BC",
    ]
    assert analysis.redundant_constraint_ids == ("C3-E-AC",)


def test_non_graph_relation_is_preserved() -> None:
    tangent = _constraint("C-T-AB", "TANGENT", ("A", "B"), confidence=0.97)

    analysis = ConstraintSystemAnalyzer().analyze(_resolution(tangent))

    assert analysis.resolution.constraints == (tangent,)
    assert analysis.redundant_constraint_ids == ()
    assert analysis.rejected_constraint_ids == ()


def test_existing_resolver_issues_are_preserved() -> None:
    issue = ConstraintIssue(
        issue_id="U-existing",
        code="UNSATISFIED_CONSTRAINT",
        message="existing issue",
        entity_ids=("A",),
    )
    resolution = ConstraintResolution(
        constraints=(_constraint("C-H-A", "HORIZONTAL", ("A",)),),
        issues=(issue,),
    )

    analysis = ConstraintSystemAnalyzer().analyze(resolution)

    assert issue in analysis.resolution.issues


def test_analysis_is_deterministic_under_constraint_reordering() -> None:
    constraints = (
        _constraint("C-H-A", "HORIZONTAL", ("A",)),
        _constraint("C-H-B", "HORIZONTAL", ("B",)),
        _constraint("C-PP-AB", "PERPENDICULAR", ("A", "B"), confidence=0.9),
        _constraint("C-E-XY", "EQUAL", ("X", "Y")),
    )
    analyzer = ConstraintSystemAnalyzer()

    forward = analyzer.analyze(ConstraintResolution(constraints=constraints, issues=()))
    reversed_result = analyzer.analyze(
        ConstraintResolution(constraints=tuple(reversed(constraints)), issues=())
    )

    assert forward == reversed_result
