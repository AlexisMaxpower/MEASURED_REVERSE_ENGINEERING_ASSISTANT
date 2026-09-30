from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from physical_measurement import (  # noqa: E402
    CanonicalMeasurementAdapter,
    HandsFreeMeasurementController,
    HandsFreePhase,
    InMemoryMeasurementSessionRepository,
    MeasurementCandidateContext,
    MeasurementSessionService,
    MeasurementType,
    OcrMeasurementPipeline,
    OcrMeasurementReader,
    OcrObservation,
    OcrReadStatus,
    ProvenanceSource,
)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-PASS8-{self._value:03d}"


def _service() -> MeasurementSessionService:
    return MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
        clock=lambda: datetime(2026, 9, 30, 4, 30, tzinfo=timezone.utc),
    )


def _controller(
    *,
    measurement_type: MeasurementType = MeasurementType.LINEAR_EXTERNAL,
    evidence_frame_id: str | None = "FRAME-OCR-1",
) -> tuple[MeasurementSessionService, str, HandsFreeMeasurementController]:
    service = _service()
    session = service.create_session("P-PASS8")
    anchor_a = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=10,
        y_px=10,
    )
    anchor_b = service.create_manual_anchor(
        view_id="VIEW-FRONT",
        reference_frame_id="REF-FRONT",
        x_px=80,
        y_px=10,
    )
    controller = HandsFreeMeasurementController(
        service=service,
        session_id=session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=measurement_type,
            view_id="VIEW-FRONT",
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            instrument_type="DIGITAL_CALIPER_DISPLAY",
        ),
    )
    return service, session.session_id, controller


def _observation(
    raw_text: str,
    *,
    confidence: float | None = 0.9,
    view_id: str = "VIEW-FRONT",
    reference_frame_id: str = "REF-FRONT",
    evidence_frame_id: str = "FRAME-OCR-1",
) -> OcrObservation:
    return OcrObservation(
        raw_text=raw_text,
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        evidence_frame_id=evidence_frame_id,
        confidence=confidence,
        provider_name="fixture-ocr",
    )


def _capture_package() -> dict[str, object]:
    return {
        "schema_version": "mrea.capture-package.v1",
        "capture_package_id": "CP-PASS8",
        "project_id": "P-PASS8",
        "part_id": "PART-PASS8",
        "views": [
            {
                "view_id": "VIEW-FRONT",
                "view_type": "FRONT",
                "clean_reference_frame": {
                    "artifact_id": "REF-FRONT",
                    "uri": "fixture://pass8/front.png",
                },
                "measurement_frames": [
                    {
                        "frame_id": "FRAME-OCR-1",
                        "uri": "fixture://pass8/caliper-display.png",
                    }
                ],
            }
        ],
    }


def test_reader_accepts_decimal_comma_and_mm() -> None:
    result = OcrMeasurementReader().read(_observation("42,18 мм"), expected_unit="mm")

    assert result.status is OcrReadStatus.VALUE
    assert result.proposal is not None
    assert result.proposal.value == Decimal("42.18")
    assert result.proposal.unit == "mm"
    assert result.proposal.source is ProvenanceSource.OCR_MEASURED
    assert result.proposal.confidence == 0.9


def test_reader_accepts_angle_degree_symbol() -> None:
    result = OcrMeasurementReader().read(_observation("45°"), expected_unit="deg")

    assert result.status is OcrReadStatus.VALUE
    assert result.proposal is not None
    assert result.proposal.value == Decimal("45")
    assert result.proposal.unit == "deg"


def test_reader_nfkc_normalizes_full_width_digits() -> None:
    result = OcrMeasurementReader().read(_observation("４２，１８ mm"), expected_unit="mm")

    assert result.status is OcrReadStatus.VALUE
    assert result.proposal is not None
    assert result.proposal.value == Decimal("42.18")


def test_reader_reports_no_value_multiple_values_and_junk() -> None:
    reader = OcrMeasurementReader()

    assert reader.read(_observation("---"), expected_unit="mm").status is OcrReadStatus.NO_VALUE
    assert (
        reader.read(_observation("42.18 43.00"), expected_unit="mm").status
        is OcrReadStatus.AMBIGUOUS
    )
    assert (
        reader.read(_observation("CAL 42.18 mm"), expected_unit="mm").status
        is OcrReadStatus.INVALID
    )


def test_reader_rejects_explicit_unit_mismatch() -> None:
    result = OcrMeasurementReader().read(_observation("42.18 mm"), expected_unit="deg")

    assert result.status is OcrReadStatus.UNIT_MISMATCH
    assert result.proposal is None


def test_pipeline_derives_expected_unit_from_measurement_type() -> None:
    _, _, linear_controller = _controller(measurement_type=MeasurementType.LINEAR_EXTERNAL)
    _, _, angle_controller = _controller(measurement_type=MeasurementType.ANGLE)

    assert OcrMeasurementPipeline(
        reader=OcrMeasurementReader(), controller=linear_controller
    ).expected_unit == "mm"
    assert OcrMeasurementPipeline(
        reader=OcrMeasurementReader(), controller=angle_controller
    ).expected_unit == "deg"


def test_pipeline_requires_evidence_frame_context() -> None:
    _, _, controller = _controller(evidence_frame_id=None)

    with pytest.raises(ValueError, match="requires evidence_frame_id"):
        OcrMeasurementPipeline(reader=OcrMeasurementReader(), controller=controller)


def test_pipeline_fails_closed_on_view_reference_or_evidence_mismatch() -> None:
    _, _, controller = _controller()
    pipeline = OcrMeasurementPipeline(
        reader=OcrMeasurementReader(),
        controller=controller,
    )

    with pytest.raises(ValueError, match="view_id"):
        pipeline.process(_observation("42.18", view_id="VIEW-SIDE"))
    with pytest.raises(ValueError, match="reference_frame_id"):
        pipeline.process(_observation("42.18", reference_frame_id="REF-OTHER"))
    with pytest.raises(ValueError, match="evidence_frame_id"):
        pipeline.process(_observation("42.18", evidence_frame_id="FRAME-OTHER"))


def test_non_value_ocr_result_creates_no_measurement_candidate() -> None:
    service, session_id, controller = _controller()
    pipeline = OcrMeasurementPipeline(
        reader=OcrMeasurementReader(),
        controller=controller,
    )

    result = pipeline.process(_observation("42.18 43.00"))

    assert result.read.status is OcrReadStatus.AMBIGUOUS
    assert result.transition is None
    assert service.get_session(session_id).measurements == ()
    assert controller.state.phase is HandsFreePhase.IDLE


def test_confidence_one_still_creates_only_unverified_ocr_candidate() -> None:
    service, session_id, controller = _controller()
    pipeline = OcrMeasurementPipeline(
        reader=OcrMeasurementReader(),
        controller=controller,
    )

    result = pipeline.process(_observation("80.20 mm", confidence=1.0))

    assert result.read.status is OcrReadStatus.VALUE
    assert result.transition is not None
    measurement = result.transition.measurement
    assert measurement is not None
    assert measurement.value == Decimal("80.20")
    assert measurement.unit == "mm"
    assert measurement.source is ProvenanceSource.OCR_MEASURED
    assert measurement.evidence_frame_id == "FRAME-OCR-1"
    assert measurement.is_verified is False
    assert controller.state.phase is HandsFreePhase.CANDIDATE_PENDING
    assert service.get_session(session_id).get(measurement.measurement_id).is_verified is False


def test_ocr_candidate_requires_same_explicit_user_confirmation_as_other_sources() -> None:
    service, session_id, controller = _controller()
    pipeline = OcrMeasurementPipeline(
        reader=OcrMeasurementReader(),
        controller=controller,
    )

    pending = pipeline.process(_observation("80,20 мм", confidence=0.99))
    assert pending.transition is not None
    candidate = pending.transition.measurement
    assert candidate is not None
    assert candidate.is_verified is False

    confirmed = controller.process_voice_command("подтвердить")
    measurement = confirmed.measurement
    assert measurement is not None
    assert measurement.source is ProvenanceSource.OCR_MEASURED
    assert measurement.confirmation_source is ProvenanceSource.USER_CONFIRMED
    assert measurement.is_verified is True

    package = CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
        session=service.get_session(session_id),
        capture_package=_capture_package(),
    )
    wire = package["measurements"][0]
    assert wire["source"] == "OCR_MEASURED"
    assert wire["verified"] is True
    assert wire["confirmation_source"] == "USER_CONFIRMED"
    assert wire["evidence_frame_id"] == "FRAME-OCR-1"
    assert all(anchor["coordinate_space"] == "IMAGE_PX" for anchor in wire["anchors"])


def test_angle_pipeline_uses_deg_candidate_unit() -> None:
    _, _, controller = _controller(measurement_type=MeasurementType.ANGLE)
    pipeline = OcrMeasurementPipeline(
        reader=OcrMeasurementReader(),
        controller=controller,
    )

    result = pipeline.process(_observation("45 град"))

    assert pipeline.expected_unit == "deg"
    assert result.transition is not None
    measurement = result.transition.measurement
    assert measurement is not None
    assert measurement.unit == "deg"
    assert measurement.value == Decimal("45")
    assert measurement.is_verified is False
