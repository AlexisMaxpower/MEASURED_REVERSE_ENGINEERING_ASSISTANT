from __future__ import annotations

from mrea_geometry import Arc, Circle, ConstraintCandidateEngine, Line, Point2D, PointEntity


def _constraints(*entities):
    return {
        (item.kind, item.entity_ids)
        for item in ConstraintCandidateEngine(metric_tolerance=1e-6).build(tuple(entities))
    }


def test_coincident_detects_observed_endpoint_contact_but_not_interior_crossing() -> None:
    left = Line("L-LEFT", Point2D(0.0, 0.0), Point2D(5.0, 0.0))
    right = Line("L-RIGHT", Point2D(5.0, 0.0), Point2D(5.0, 4.0))
    crossing = Line("L-CROSS", Point2D(2.5, -2.0), Point2D(2.5, 2.0))

    values = _constraints(left, right, crossing)

    assert ("COINCIDENT", ("L-LEFT", "L-RIGHT")) in values
    assert ("COINCIDENT", ("L-CROSS", "L-LEFT")) not in values


def test_coincident_supports_explicit_point_on_circle() -> None:
    point = PointEntity("P-CONTACT", Point2D(5.0, 0.0))
    circle = Circle("C-1", Point2D(0.0, 0.0), 5.0)

    assert ("COINCIDENT", ("C-1", "P-CONTACT")) in _constraints(point, circle)


def test_line_circle_tangent_requires_contact_on_finite_segment() -> None:
    circle = Circle("C-1", Point2D(0.0, 0.0), 2.0)
    tangent = Line("L-TAN", Point2D(-4.0, 2.0), Point2D(4.0, 2.0))
    short = Line("L-SHORT", Point2D(3.0, 2.0), Point2D(4.0, 2.0))

    values = _constraints(circle, tangent, short)

    assert ("TANGENT", ("C-1", "L-TAN")) in values
    assert ("TANGENT", ("C-1", "L-SHORT")) not in values


def test_line_arc_tangent_requires_tangent_point_inside_observed_arc_span() -> None:
    upper_arc = Arc("A-UP", Point2D(0.0, 0.0), 2.0, 0.0, 180.0)
    lower_arc = Arc("A-DOWN", Point2D(0.0, 0.0), 2.0, 180.0, 360.0)
    top_line = Line("L-TOP", Point2D(-4.0, 2.0), Point2D(4.0, 2.0))

    values = _constraints(upper_arc, lower_arc, top_line)

    assert ("TANGENT", ("A-UP", "L-TOP")) in values
    assert ("TANGENT", ("A-DOWN", "L-TOP")) not in values


def test_round_round_external_and_internal_tangency_are_detected() -> None:
    outer_a = Circle("C-A", Point2D(0.0, 0.0), 2.0)
    outer_b = Circle("C-B", Point2D(5.0, 0.0), 3.0)
    containing = Circle("C-LARGE", Point2D(10.0, 0.0), 5.0)
    contained = Circle("C-SMALL", Point2D(13.0, 0.0), 2.0)

    values = _constraints(outer_a, outer_b, containing, contained)

    assert ("TANGENT", ("C-A", "C-B")) in values
    assert ("TANGENT", ("C-LARGE", "C-SMALL")) in values


def test_arc_round_tangency_is_rejected_when_contact_is_outside_arc_span() -> None:
    arc = Arc("A-LEFT", Point2D(0.0, 0.0), 2.0, 90.0, 270.0)
    circle = Circle("C-RIGHT", Point2D(5.0, 0.0), 3.0)

    assert ("TANGENT", ("A-LEFT", "C-RIGHT")) not in _constraints(arc, circle)


def test_symmetric_points_require_explicit_axis_line() -> None:
    axis = Line("L-AXIS", Point2D(0.0, -10.0), Point2D(0.0, 10.0))
    left = PointEntity("P-L", Point2D(-3.0, 2.0))
    right = PointEntity("P-R", Point2D(3.0, 2.0))

    values = _constraints(axis, left, right)

    assert ("SYMMETRIC", ("P-L", "P-R", "L-AXIS")) in values
    assert not any(kind == "SYMMETRIC" for kind, _ in _constraints(left, right))


def test_symmetric_circles_require_equal_radius_and_reflected_centers() -> None:
    axis = Line("L-AXIS", Point2D(0.0, -10.0), Point2D(0.0, 10.0))
    left = Circle("C-L", Point2D(-4.0, 1.0), 1.5)
    right = Circle("C-R", Point2D(4.0, 1.0), 1.5)
    wrong_radius = Circle("C-WRONG", Point2D(4.0, 1.0), 2.0)

    values = _constraints(axis, left, right, wrong_radius)

    assert ("SYMMETRIC", ("C-L", "C-R", "L-AXIS")) in values
    assert ("SYMMETRIC", ("C-L", "C-WRONG", "L-AXIS")) not in values


def test_candidate_output_is_deterministic_under_entity_reordering() -> None:
    entities = (
        Line("L-AXIS", Point2D(0.0, -10.0), Point2D(0.0, 10.0)),
        PointEntity("P-L", Point2D(-3.0, 2.0)),
        PointEntity("P-R", Point2D(3.0, 2.0)),
        Circle("C-1", Point2D(0.0, 0.0), 2.0),
        Line("L-TAN", Point2D(-4.0, 2.0), Point2D(4.0, 2.0)),
    )
    engine = ConstraintCandidateEngine()

    assert engine.build(entities) == engine.build(tuple(reversed(entities)))
