from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    CanonicalMeasurementAdapter,
    FeatureAnchorSelector,
    FeatureSnapCandidate,
    FeatureSnapProposal,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
    ProvenanceSource,
    SnapSelectionStatus,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS7-{self._value:03d}"


def _service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 3, 30, tzinfo=timezone.utc),
    )


def _capture_package() -> dict[str, object]:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS7",
        "project_id": "P-PASS7",
        "part_id": "PART-PASS7",
        "views": [
            {
                "view_id": "VIEW-FRONT",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "REF-FRONT",
                    "uri": "fixture://pass7/front.png",
                },
                "measurement_frames": [],
            }
        ],
    }


def _candidate(
    feature_id: str,
    x: float,
    y: float,
    *,
    confidence: float | None = None,
    view_id: str = "VIEW-FRONT",
    reference_frame_id: str = "REF-FRONT",
) -> FeatureSnapCandidate:
    return FeatureSnapCandidate(
        feature_id=feature_id,
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=x,
        y_px=y,
        confidence=confidence,
    )


def test_selector_picks_nearest_feature_not_highest_confidence() -> None:
    service = _service()
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    selector = FeatureAnchorSelector(max_distance_px=5, ambiguity_epsilon_px=0.1)

    selection = selector.select(
        anchor=anchor,
        candidates=[
            _candidate("FEATURE-NEAR", 11, 10, confidence=0.55),
            _candidate("FEATURE-FAR", 13, 10, confidence=0.99),
        ],
    )

    assert selection.status is SnapSelectionStatus.MATCH
    assert selection.proposal is not None
    assert selection.proposal.feature_id == "FEATURE-NEAR"
    assert selection.proposal.distance_px == pytest.approx(1.0)
    assert selection.proposal.source is ProvenanceSource.VISION_DETECTED


def test_selector_returns_no_match_outside_threshold_or_frame() -> None:
    service = _service()
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    selector = FeatureAnchorSelector(max_distance_px=2)

    selection = selector.select(
        anchor=anchor,
        candidates=[
            _candidate("FEATURE-FAR", 20, 10),
            _candidate("FEATURE-SIDE", 10.5, 10, view_id="VIEW-SIDE"),
            _candidate("FEATURE-OTHER-REF", 10.5, 10, reference_frame_id="REF-OTHER"),
        ],
    )

    assert selection.status is SnapSelectionStatus.NO_MATCH
    assert selection.proposal is None


def test_selector_reports_near_tie_as_ambiguous() -> None:
    service = _service()
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    selector = FeatureAnchorSelector(max_distance_px=3, ambiguity_epsilon_px=0.25)

    selection = selector.select(
        anchor=anchor,
        candidates=[
            _candidate("FEATURE-A", 11.0, 10),
            _candidate("FEATURE-B", 11.2, 10),
        ],
    )

    assert selection.status is SnapSelectionStatus.AMBIGUOUS
    assert selection.proposal is None
    assert selection.competing_feature_ids == ("FEATURE-A", "FEATURE-B")


def test_selector_rejects_duplicate_feature_ids() -> None:
    service = _service()
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    selector = FeatureAnchorSelector(max_distance_px=3)

    with pytest.raises(ValueError, match="duplicate feature_id"):
        selector.select(
            anchor=anchor,
            candidates=[
                _candidate("FEATURE-1", 11, 10),
                _candidate("FEATURE-1", 12, 10),
            ],
        )


def test_apply_snap_requires_explicit_acceptance() -> None:
    service = _service()
    session = service.create_session("P-PASS7")
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    measurement = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.DEPTH,
        value="3.2",
        view_id="VIEW-FRONT",
        anchor_a=anchor,
    )
    proposal = FeatureAnchorSelector(max_distance_px=5).select(
        anchor=anchor,
        candidates=[_candidate("FEATURE-EDGE-1", 11, 10)],
    ).proposal
    assert proposal is not None

    with pytest.raises(ValueError, match="explicit user acceptance"):
        service.apply_anchor_snap(
            session_id=session.session_id,
            measurement_id=measurement.measurement_id,
            proposal=proposal,
            explicit_user_acceptance=False,
        )

    unchanged = service.get_session(session.session_id).get(measurement.measurement_id)
    assert unchanged.anchor_a.feature_id is None
    assert unchanged.anchor_a.x_px == 10


def test_accepted_snap_updates_anchor_but_does_not_verify_measurement() -> None:
    service = _service()
    session = service.create_session("P-PASS7")
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    measurement = service.add_reported_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.DEPTH,
        value="3.2",
        source=ProvenanceSource.VOICE_REPORTED,
        view_id="VIEW-FRONT",
        anchor_a=anchor,
    )
    selection = FeatureAnchorSelector(max_distance_px=5).select(
        anchor=anchor,
        candidates=[_candidate("FEATURE-EDGE-1", 11.5, 10.25, confidence=0.8)],
    )
    assert selection.proposal is not None

    updated = service.apply_anchor_snap(
        session_id=session.session_id,
        measurement_id=measurement.measurement_id,
        proposal=selection.proposal,
        explicit_user_acceptance=True,
    )

    assert updated.anchor_a.anchor_id == anchor.anchor_id
    assert updated.anchor_a.feature_id == "FEATURE-EDGE-1"
    assert updated.anchor_a.x_px == 11.5
    assert updated.anchor_a.y_px == 10.25
    assert updated.source is ProvenanceSource.VOICE_REPORTED
    assert updated.is_verified is False

    package = CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=_capture_package(),
    )
    wire = package["measurements"][0]
    assert wire["verified"] is False
    assert wire["source"] == "VOICE_REPORTED"
    assert wire["anchors"][0]["feature_id"] == "FEATURE-EDGE-1"
    assert wire["anchors"][0]["coordinate_space"] == "IMAGE_PX"
    assert wire["anchors"][0]["x"] == 11.5
    assert wire["anchors"][0]["y"] == 10.25


def test_verified_measurement_cannot_be_resnapped() -> None:
    service = _service()
    session = service.create_session("P-PASS7")
    anchor = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    measurement = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.DEPTH,
        value="3.2",
        view_id="VIEW-FRONT",
        anchor_a=anchor,
    )
    verified = service.confirm_measurement(
        session_id=session.session_id,
        measurement_id=measurement.measurement_id,
        explicit_user_confirmation=True,
    )
    proposal = FeatureAnchorSelector(max_distance_px=5).select(
        anchor=anchor,
        candidates=[_candidate("FEATURE-EDGE-1", 11, 10)],
    ).proposal
    assert proposal is not None

    with pytest.raises(ValueError, match="verified measurement anchors cannot be modified"):
        service.apply_anchor_snap(
            session_id=session.session_id,
            measurement_id=verified.measurement_id,
            proposal=proposal,
            explicit_user_acceptance=True,
        )


def test_handcrafted_proposal_fails_closed_on_wrong_provenance() -> None:
    with pytest.raises(ValueError, match="VISION_DETECTED"):
        FeatureSnapProposal(
            anchor_id="A-1",
            feature_id="FEATURE-1",
            view_id="VIEW-FRONT",
            reference_frame_id="REF-FRONT",
            x_px=10,
            y_px=10,
            distance_px=1,
            confidence=0.9,
            source=ProvenanceSource.AI_INFERRED,
        )
