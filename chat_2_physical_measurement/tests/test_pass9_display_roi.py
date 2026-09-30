from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    DisplayRoiCandidate,
    DisplayRoiOcrBridge,
    DisplayRoiSelector,
    HandsFreeMeasurementController,
    InMemoryMeasurementSessionRepository,
    MeasurementCandidateContext,
    MeasurementSessionService,
    MeasurementType,
    OcrMeasurementPipeline,
    OcrMeasurementReader,
    ProvenanceSource,
    RoiSelectionStatus,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS9-{self._value:03d}"


def _candidate(roi_id: str, confidence: float, *, view: str = "VIEW-FRONT", ref: str = "REF-FRONT", frame: str = "FRAME-OCR-1") -> DisplayRoiCandidate:
    return DisplayRoiCandidate(
        roi_id=roi_id,
        view_id=view,
        reference_frame_id=ref,
        evidence_frame_id=frame,
        x_px=100,
        y_px=40,
        width_px=220,
        height_px=80,
        confidence=confidence,
        provider_name="fixture-detector",
    )


def _controller() -> tuple[MeasurementSessionService, str, HandsFreeMeasurementController]:
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 5, 0, tzinfo=timezone.utc),
    )
    session = service.create_session("P-PASS9")
    a = service.create_manual_anchor(view_id="VIEW-FRONT", reference_frame_id="REF-FRONT", x_px=10, y_px=10)
    b = service.create_manual_anchor(view_id="VIEW-FRONT", reference_frame_id="REF-FRONT", x_px=80, y_px=10)
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            view_id="VIEW-FRONT",
            anchor_a=a,
            anchor_b=b,
            evidence_frame_id="FRAME-OCR-1",
        ),
    )
    return service, session.session_id, controller


def test_selector_chooses_highest_confidence_in_exact_context() -> None:
    selector = DisplayRoiSelector(min_confidence=0.5, ambiguity_epsilon=0.01)
    result = selector.select(
        [_candidate("ROI-A", 0.70), _candidate("ROI-B", 0.95)],
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert result.status is RoiSelectionStatus.MATCH
    assert result.proposal is not None
    assert result.proposal.roi_id == "ROI-B"


def test_selector_fails_closed_on_no_match_and_ambiguity() -> None:
    selector = DisplayRoiSelector(min_confidence=0.5, ambiguity_epsilon=0.02)
    no_match = selector.select(
        [_candidate("ROI-A", 0.95, view="VIEW-SIDE")],
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert no_match.status is RoiSelectionStatus.NO_MATCH

    ambiguous = selector.select(
        [_candidate("ROI-A", 0.95), _candidate("ROI-B", 0.94)],
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert ambiguous.status is RoiSelectionStatus.AMBIGUOUS
    assert ambiguous.proposal is None


def test_duplicate_ids_and_invalid_bbox_fail_closed() -> None:
    selector = DisplayRoiSelector()
    with pytest.raises(ValueError, match="duplicate"):
        selector.select(
            [_candidate("ROI-A", 0.8), _candidate("ROI-A", 0.9)],
            view_id="VIEW-FRONT",
            reference_frame_id="REF-FRONT",
            evidence_frame_id="FRAME-OCR-1",
        )
    with pytest.raises(ValueError, match="width/height"):
        DisplayRoiCandidate(
            roi_id="ROI-X", view_id="VIEW-FRONT", reference_frame_id="REF-FRONT",
            evidence_frame_id="FRAME-OCR-1", x_px=0, y_px=0, width_px=0, height_px=10,
            confidence=0.9,
        )


def test_roi_bridge_preserves_roi_metadata_into_ocr_proposal() -> None:
    selector = DisplayRoiSelector()
    selection = selector.select(
        [_candidate("ROI-A", 0.91)],
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert selection.proposal is not None
    observation = DisplayRoiOcrBridge.build_observation(
        proposal=selection.proposal,
        raw_text="80,20 mm",
        ocr_confidence=0.99,
        ocr_provider_name="fixture-ocr",
    )
    read = OcrMeasurementReader().read(observation, expected_unit="mm")
    assert read.proposal is not None
    assert read.proposal.roi_id == "ROI-A"
    assert read.proposal.roi_bbox_px == (100, 40, 220, 80)
    assert read.proposal.roi_confidence == 0.91
    assert read.proposal.roi_provider_name == "fixture-detector"


def test_roi_to_ocr_pipeline_still_creates_only_unverified_candidate() -> None:
    service, session_id, controller = _controller()
    selection = DisplayRoiSelector().select(
        [_candidate("ROI-A", 1.0)],
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert selection.proposal is not None
    observation = DisplayRoiOcrBridge.build_observation(
        proposal=selection.proposal,
        raw_text="80.20 mm",
        ocr_confidence=1.0,
        ocr_provider_name="fixture-ocr",
    )
    result = OcrMeasurementPipeline(reader=OcrMeasurementReader(), controller=controller).process(observation)
    assert result.transition is not None
    measurement = result.transition.measurement
    assert measurement is not None
    assert measurement.source is ProvenanceSource.OCR_MEASURED
    assert measurement.is_verified is False
    assert service.get_session(session_id).get(measurement.measurement_id).is_verified is False


def test_roi_from_wrong_context_is_rejected_by_ocr_pipeline() -> None:
    _, _, controller = _controller()
    wrong = _candidate("ROI-X", 0.99, view="VIEW-SIDE")
    observation = DisplayRoiOcrBridge.build_observation(
        proposal=DisplayRoiSelector().select(
            [wrong], view_id="VIEW-SIDE", reference_frame_id="REF-FRONT", evidence_frame_id="FRAME-OCR-1"
        ).proposal,
        raw_text="80.20 mm",
    )
    with pytest.raises(ValueError, match="view_id"):
        OcrMeasurementPipeline(reader=OcrMeasurementReader(), controller=controller).process(observation)


def test_plain_ocr_observation_without_roi_remains_backward_compatible() -> None:
    from physical_measurement import OcrObservation
    observation = OcrObservation(
        raw_text="42.18 mm",
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        evidence_frame_id="FRAME-OCR-1",
    )
    assert observation.roi_id is None
    assert OcrMeasurementReader().read(observation, expected_unit="mm").proposal is not None
