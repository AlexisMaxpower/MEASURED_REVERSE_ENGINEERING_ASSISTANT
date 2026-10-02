from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from physical_measurement import (
    AmbiguousOcrMeasurement,
    DisplayRoi,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
    OcrMeasurementContext,
    OcrMeasurementError,
    OcrMeasurementIntake,
    OcrMeasurementReader,
    OcrTextObservation,
    ProvenanceSource,
)


class PrefixSequentialIds:
    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._values[prefix] += 1
        return f"{prefix}-CHAT2-P19-{self._values[prefix]:03d}"


def build_service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: datetime(2026, 10, 2, 2, 0, 0, tzinfo=timezone.utc),
    )


def build_context(
    service: MeasurementSessionService,
    *,
    measurement_type: MeasurementType = MeasurementType.LINEAR_EXTERNAL,
    view_id: str = "VIEW-P19",
    evidence_frame_id: str = "FRAME-P19",
) -> OcrMeasurementContext:
    anchor_a = service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id="REF-P19",
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id="REF-P19",
        x_px=520,
        y_px=200,
    )
    return OcrMeasurementContext(
        measurement_type=measurement_type,
        view_id=view_id,
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id=evidence_frame_id,
        uncertainty="0.02" if measurement_type is not MeasurementType.ANGLE else "0.1",
        instrument_type="DIGITAL_CALIPER",
    )


def observation(
    text: str,
    *,
    view_id: str = "VIEW-P19",
    evidence_frame_id: str = "FRAME-P19",
    confidence: float | None = 0.73,
) -> OcrTextObservation:
    return OcrTextObservation(
        text=text,
        roi=DisplayRoi(
            view_id=view_id,
            evidence_frame_id=evidence_frame_id,
            x_px=310,
            y_px=120,
            width_px=180,
            height_px=72,
        ),
        confidence=confidence,
        provider_id="TEST-OCR",
    )


def test_reader_produces_mm_proposal_without_verification_semantics() -> None:
    proposal = OcrMeasurementReader().read(
        observation=observation(" 42,18 mm "),
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
    )

    assert proposal.value == Decimal("42.18")
    assert proposal.unit == "mm"
    assert proposal.source is ProvenanceSource.OCR_MEASURED
    assert proposal.observation.confidence == pytest.approx(0.73)
    assert proposal.observation.roi.evidence_frame_id == "FRAME-P19"


def test_reader_accepts_degree_symbol_only_for_angle_context() -> None:
    proposal = OcrMeasurementReader().read(
        observation=observation("12.5°"),
        measurement_type=MeasurementType.ANGLE,
    )

    assert proposal.value == Decimal("12.5")
    assert proposal.unit == "deg"


def test_reader_rejects_explicit_unit_mismatch() -> None:
    with pytest.raises(OcrMeasurementError, match="does not match measurement type"):
        OcrMeasurementReader().read(
            observation=observation("42.18 deg"),
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
        )


def test_reader_fails_closed_on_multiple_numeric_values() -> None:
    with pytest.raises(AmbiguousOcrMeasurement, match="multiple numeric values"):
        OcrMeasurementReader().read(
            observation=observation("42.18 42.16"),
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
        )


def test_reader_does_not_silently_correct_ocr_character_confusions() -> None:
    with pytest.raises(OcrMeasurementError, match="no silent correction"):
        OcrMeasurementReader().read(
            observation=observation("4O.18 mm"),
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("x_px", -1),
        ("width_px", 0),
        ("height_px", float("inf")),
    ],
)
def test_display_roi_rejects_invalid_geometry(field: str, value: float) -> None:
    kwargs = {
        "view_id": "VIEW-P19",
        "evidence_frame_id": "FRAME-P19",
        "x_px": 0,
        "y_px": 0,
        "width_px": 100,
        "height_px": 50,
    }
    kwargs[field] = value
    with pytest.raises(OcrMeasurementError):
        DisplayRoi(**kwargs)


def test_observation_rejects_invalid_confidence() -> None:
    with pytest.raises(OcrMeasurementError, match="confidence"):
        observation("42.18", confidence=1.01)


def test_intake_creates_only_unverified_ocr_candidate_and_preserves_evidence() -> None:
    service = build_service()
    session = service.create_session("PROJECT-P19")
    context = build_context(service)
    intake = OcrMeasurementIntake(service=service)

    candidate = intake.propose_candidate(
        session_id=session.session_id,
        context=context,
        observation=observation("42.18 mm", confidence=0.41),
    )

    assert candidate.value == Decimal("42.18")
    assert candidate.unit == "mm"
    assert candidate.source is ProvenanceSource.OCR_MEASURED
    assert candidate.is_verified is False
    assert candidate.confirmation_source is None
    assert candidate.evidence_frame_id == "FRAME-P19"
    assert candidate.view_id == "VIEW-P19"
    assert candidate.anchor_a == context.anchor_a
    assert candidate.anchor_b == context.anchor_b

    stored = service.get_session(session.session_id).get(candidate.measurement_id)
    assert stored == candidate
    assert stored.is_verified is False

    confirmed = service.confirm_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )
    assert confirmed.is_verified is True
    assert confirmed.source is ProvenanceSource.OCR_MEASURED
    assert confirmed.confirmation_source is ProvenanceSource.USER_CONFIRMED


def test_low_provider_confidence_never_auto_verifies_candidate() -> None:
    service = build_service()
    session = service.create_session("PROJECT-P19")
    candidate = OcrMeasurementIntake(service=service).propose_candidate(
        session_id=session.session_id,
        context=build_context(service),
        observation=observation("42.18", confidence=0.01),
    )

    assert candidate.is_verified is False
    assert candidate.source is ProvenanceSource.OCR_MEASURED


def test_roi_view_mismatch_fails_before_session_mutation() -> None:
    service = build_service()
    session = service.create_session("PROJECT-P19")
    context = build_context(service)

    with pytest.raises(OcrMeasurementError, match="view_id"):
        OcrMeasurementIntake(service=service).propose_candidate(
            session_id=session.session_id,
            context=context,
            observation=observation("42.18", view_id="OTHER-VIEW"),
        )

    assert service.get_session(session.session_id).measurements == ()


def test_roi_evidence_frame_mismatch_fails_before_session_mutation() -> None:
    service = build_service()
    session = service.create_session("PROJECT-P19")
    context = build_context(service)

    with pytest.raises(OcrMeasurementError, match="evidence_frame_id"):
        OcrMeasurementIntake(service=service).propose_candidate(
            session_id=session.session_id,
            context=context,
            observation=observation("42.18", evidence_frame_id="OTHER-FRAME"),
        )

    assert service.get_session(session.session_id).measurements == ()


def test_unit_mismatch_fails_before_session_mutation() -> None:
    service = build_service()
    session = service.create_session("PROJECT-P19")
    context = build_context(service)

    with pytest.raises(OcrMeasurementError, match="does not match measurement type"):
        OcrMeasurementIntake(service=service).propose_candidate(
            session_id=session.session_id,
            context=context,
            observation=observation("42.18°"),
        )

    assert service.get_session(session.session_id).measurements == ()


def test_ocr_context_requires_evidence_frame() -> None:
    service = build_service()
    anchor = service.create_manual_anchor(
        view_id="VIEW-P19",
        reference_frame_id="REF-P19",
        x_px=1,
        y_px=2,
    )

    with pytest.raises(OcrMeasurementError, match="requires evidence_frame_id"):
        OcrMeasurementContext(
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            view_id="VIEW-P19",
            anchor_a=anchor,
            evidence_frame_id=None,
        )
