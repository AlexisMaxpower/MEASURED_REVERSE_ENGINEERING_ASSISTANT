from __future__ import annotations

import math

import pytest

from physical_measurement import (
    AmbiguousAnchorSnap,
    AnchorSelectionError,
    AnchorSnapTarget,
    FeatureAnchorSelector,
    ManualAnchorPick,
    ProvenanceSource,
)


def raw_pick(*, x_px: float = 100.0, y_px: float = 200.0) -> ManualAnchorPick:
    return ManualAnchorPick(
        view_id="VIEW-P18",
        reference_frame_id="REF-P18",
        x_px=x_px,
        y_px=y_px,
    )


def snap_target(
    target_id: str,
    *,
    x_px: float,
    y_px: float,
    view_id: str = "VIEW-P18",
    reference_frame_id: str = "REF-P18",
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED,
) -> AnchorSnapTarget:
    return AnchorSnapTarget(
        target_id=target_id,
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=x_px,
        y_px=y_px,
        source=source,
    )


def test_nearest_same_context_target_is_proposed_independent_of_input_order() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick()
    near = snap_target("FEATURE-NEAR", x_px=103.0, y_px=204.0)
    far = snap_target("FEATURE-FAR", x_px=108.0, y_px=206.0)

    first = selector.propose_snap(
        raw_pick=pick,
        targets=[far, near],
        snap_radius_px=12.0,
    )
    second = selector.propose_snap(
        raw_pick=pick,
        targets=[near, far],
        snap_radius_px=12.0,
    )

    assert first is not None
    assert second is not None
    assert first.target.target_id == second.target.target_id == "FEATURE-NEAR"
    assert first.distance_px == second.distance_px == pytest.approx(5.0)
    assert first.raw_pick == pick


def test_wrong_context_and_out_of_radius_targets_are_not_actionable() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick()

    proposal = selector.propose_snap(
        raw_pick=pick,
        targets=[
            snap_target(
                "OTHER-VIEW",
                x_px=100.0,
                y_px=200.0,
                view_id="VIEW-OTHER",
            ),
            snap_target(
                "OTHER-REF",
                x_px=100.0,
                y_px=200.0,
                reference_frame_id="REF-OTHER",
            ),
            snap_target("TOO-FAR", x_px=120.0, y_px=200.0),
        ],
        snap_radius_px=10.0,
    )

    assert proposal is None


def test_equal_distance_targets_fail_closed_instead_of_using_id_or_input_order() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick()

    with pytest.raises(AmbiguousAnchorSnap):
        selector.propose_snap(
            raw_pick=pick,
            targets=[
                snap_target("LEFT", x_px=99.0, y_px=200.0),
                snap_target("RIGHT", x_px=101.0, y_px=200.0),
            ],
            snap_radius_px=5.0,
        )


def test_duplicate_target_ids_fail_closed_even_when_coordinates_differ() -> None:
    selector = FeatureAnchorSelector()

    with pytest.raises(AnchorSelectionError, match="duplicate snap target_id"):
        selector.propose_snap(
            raw_pick=raw_pick(),
            targets=[
                snap_target("DUPLICATE", x_px=101.0, y_px=200.0),
                snap_target("DUPLICATE", x_px=102.0, y_px=200.0),
            ],
            snap_radius_px=5.0,
        )


def test_snap_target_must_remain_vision_detected_advice() -> None:
    with pytest.raises(AnchorSelectionError, match="VISION_DETECTED"):
        snap_target(
            "AI-TARGET",
            x_px=101.0,
            y_px=200.0,
            source=ProvenanceSource.AI_INFERRED,
        )

    with pytest.raises(AnchorSelectionError, match="VISION_DETECTED"):
        snap_target(
            "MEASURED-TARGET",
            x_px=101.0,
            y_px=200.0,
            source=ProvenanceSource.MANUAL_MEASURED,
        )


def test_proposal_never_becomes_anchor_without_explicit_user_acceptance() -> None:
    selector = FeatureAnchorSelector()
    proposal = selector.propose_snap(
        raw_pick=raw_pick(),
        targets=[snap_target("FEATURE-1", x_px=102.0, y_px=201.0)],
        snap_radius_px=5.0,
    )
    assert proposal is not None

    with pytest.raises(AnchorSelectionError, match="explicit user confirmation"):
        selector.accept_snap(
            proposal=proposal,
            explicit_user_confirmation=False,
        )


def test_accepted_snap_preserves_detection_and_confirmation_provenance() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick()
    proposal = selector.propose_snap(
        raw_pick=pick,
        targets=[snap_target("FEATURE-1", x_px=102.0, y_px=201.0)],
        snap_radius_px=5.0,
    )
    assert proposal is not None

    selection = selector.accept_snap(
        proposal=proposal,
        explicit_user_confirmation=True,
    )

    assert selection.snapped is True
    assert selection.x_px == 102.0
    assert selection.y_px == 201.0
    assert selection.raw_x_px == pick.x_px
    assert selection.raw_y_px == pick.y_px
    assert selection.snap_target_id == "FEATURE-1"
    assert selection.source is ProvenanceSource.VISION_DETECTED
    assert selection.confirmation_source is ProvenanceSource.USER_CONFIRMED

    anchor = selection.build_anchor(anchor_id="A-P18-SNAPPED")
    assert anchor.anchor_id == "A-P18-SNAPPED"
    assert anchor.view_id == "VIEW-P18"
    assert anchor.reference_frame_id == "REF-P18"
    assert anchor.x_px == 102.0
    assert anchor.y_px == 201.0


def test_keep_raw_preserves_manual_image_point_and_manual_provenance() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick(x_px=123.25, y_px=456.75)

    selection = selector.keep_raw(raw_pick=pick)

    assert selection.snapped is False
    assert selection.x_px == selection.raw_x_px == 123.25
    assert selection.y_px == selection.raw_y_px == 456.75
    assert selection.source is ProvenanceSource.MANUAL_MEASURED
    assert selection.confirmation_source is None
    assert selection.snap_target_id is None

    anchor = selection.build_anchor(anchor_id="A-P18-RAW")
    assert anchor.x_px == 123.25
    assert anchor.y_px == 456.75


def test_radius_boundary_is_inclusive_but_invalid_radius_fails_closed() -> None:
    selector = FeatureAnchorSelector()
    pick = raw_pick()

    proposal = selector.propose_snap(
        raw_pick=pick,
        targets=[snap_target("ON-BOUNDARY", x_px=103.0, y_px=204.0)],
        snap_radius_px=5.0,
    )
    assert proposal is not None
    assert proposal.distance_px == pytest.approx(5.0)

    for invalid_radius in (0.0, -1.0, math.inf, math.nan):
        with pytest.raises(AnchorSelectionError):
            selector.propose_snap(
                raw_pick=pick,
                targets=[],
                snap_radius_px=invalid_radius,
            )


def test_invalid_image_coordinates_fail_closed() -> None:
    for invalid in (-1.0, math.inf, math.nan):
        with pytest.raises(AnchorSelectionError):
            raw_pick(x_px=invalid)

    with pytest.raises(AnchorSelectionError):
        ManualAnchorPick(
            view_id="VIEW-P18",
            reference_frame_id="REF-P18",
            x_px=True,
            y_px=1.0,
        )
