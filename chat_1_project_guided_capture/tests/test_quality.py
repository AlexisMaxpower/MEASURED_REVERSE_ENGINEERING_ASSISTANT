from pathlib import Path
from uuid import UUID

import cv2
import numpy as np
import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureQualityVerdict,
    CaptureViewType,
    MeasurementMatProfile,
    PartContext,
    Project,
    QualityReasonCode,
)
from mrea_capture.quality import (
    CaptureQualityError,
    CaptureQualityService,
    OpenCvCaptureQualityAnalyzer,
    RussianQualityGuidanceAdapter,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


FRAME_ID = UUID("00000000-0000-0000-0000-000000000123")


def _encode(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def _good_image() -> np.ndarray:
    image = np.full((480, 640, 3), 128, dtype=np.uint8)
    x0, y0, x1, y1 = 160, 100, 480, 380
    block = 40
    for y in range(y0, y1, block):
        for x in range(x0, x1, block):
            value = 55 if ((x - x0) // block + (y - y0) // block) % 2 == 0 else 205
            cv2.rectangle(
                image,
                (x, y),
                (min(x + block - 1, x1 - 1), min(y + block - 1, y1 - 1)),
                (value, value, value),
                -1,
            )
    cv2.circle(image, (320, 240), 45, (90, 160, 200), -1)
    cv2.line(image, (190, 330), (450, 150), (180, 70, 110), 5)
    return image


def _full_frame_pattern() -> np.ndarray:
    image = np.empty((480, 640, 3), dtype=np.uint8)
    block = 32
    for y in range(0, 480, block):
        for x in range(0, 640, block):
            value = 55 if (x // block + y // block) % 2 == 0 else 205
            cv2.rectangle(
                image,
                (x, y),
                (min(x + block - 1, 639), min(y + block - 1, 479)),
                (value, value, value),
                -1,
            )
    return image


def _codes(result) -> set[QualityReasonCode]:
    return {item.code for item in result.findings}


def test_good_capture_is_accepted_and_deterministic() -> None:
    analyzer = OpenCvCaptureQualityAnalyzer()
    image_bytes = _encode(_good_image())

    first = analyzer.analyze(
        image_bytes,
        source_frame_id=FRAME_ID,
        view=CaptureViewType.FRONT,
    )
    second = analyzer.analyze(
        image_bytes,
        source_frame_id=FRAME_ID,
        view=CaptureViewType.FRONT,
    )

    assert first == second
    assert first.verdict is CaptureQualityVerdict.ACCEPT
    assert first.findings == []
    assert first.metrics.laplacian_variance > 70
    assert first.metrics.edge_density > 0.01
    assert first.metrics.border_edge_ratio < 0.22
    assert RussianQualityGuidanceAdapter.messages(first) == [
        "Кадр пригоден для дальнейшего capture workflow."
    ]


@pytest.mark.parametrize(
    ("transform", "expected_code"),
    [
        (
            lambda image: cv2.GaussianBlur(image, (31, 31), 8),
            QualityReasonCode.BLUR,
        ),
        (
            lambda image: np.clip(image.astype(np.float32) * 0.08, 0, 255).astype(np.uint8),
            QualityReasonCode.UNDEREXPOSED,
        ),
        (
            lambda image: np.clip(image.astype(np.int16) * 0.08 + 235, 0, 255).astype(np.uint8),
            QualityReasonCode.OVEREXPOSED,
        ),
    ],
)
def test_rejects_clear_blur_and_exposure_failures(transform, expected_code) -> None:
    analyzer = OpenCvCaptureQualityAnalyzer()
    result = analyzer.analyze(
        _encode(transform(_good_image())),
        source_frame_id=FRAME_ID,
        view=CaptureViewType.FRONT,
    )

    assert result.verdict is CaptureQualityVerdict.REJECT
    assert expected_code in _codes(result)


def test_glare_and_border_framing_are_machine_readable_warnings() -> None:
    analyzer = OpenCvCaptureQualityAnalyzer()

    glare = _good_image()
    cv2.circle(glare, (270, 210), 23, (255, 255, 255), -1)
    cv2.circle(glare, (380, 280), 18, (255, 255, 255), -1)
    glare_result = analyzer.analyze(
        _encode(glare),
        source_frame_id=FRAME_ID,
        view=CaptureViewType.FRONT,
    )
    framing_result = analyzer.analyze(
        _encode(_full_frame_pattern()),
        source_frame_id=UUID(int=456),
        view=CaptureViewType.FRONT,
    )

    assert glare_result.verdict is CaptureQualityVerdict.WARN
    assert QualityReasonCode.GLARE_RISK in _codes(glare_result)
    assert glare_result.metrics.glare_proxy_fraction > 0.005

    assert framing_result.verdict is CaptureQualityVerdict.WARN
    assert QualityReasonCode.FRAMING_BORDER_ACTIVITY in _codes(framing_result)
    assert framing_result.metrics.border_edge_ratio > 0.22

    guidance = RussianQualityGuidanceAdapter.messages(glare_result)
    assert guidance == ["Есть риск бликов: измените угол камеры или источника света."]


def test_low_marker_visibility_reuses_calibration_evidence() -> None:
    profile = MeasurementMatProfile(
        mat_id="MAT-A4-V1",
        squares_x=5,
        squares_y=7,
        square_length_mm=20,
        marker_length_mm=14,
    )
    calibration = CalibrationResult(
        view=CaptureViewType.FRONT,
        source_frame_id=FRAME_ID,
        mat_id=profile.mat_id,
        homography=[1, 0, 0, 0, 1, 0, 0, 0, 1],
        detected_marker_count=3,
        detected_charuco_corner_count=5,
        reprojection_rmse_mm=0.1,
    )

    result = OpenCvCaptureQualityAnalyzer().analyze(
        _encode(_good_image()),
        source_frame_id=FRAME_ID,
        view=CaptureViewType.FRONT,
        calibration=calibration,
        mat_profile=profile,
    )

    assert result.metrics.marker_corner_visibility == pytest.approx(5 / 24)
    assert result.verdict is CaptureQualityVerdict.REJECT
    assert QualityReasonCode.LOW_MARKER_VISIBILITY in _codes(result)


def test_quality_service_persists_result_without_changing_canonical_package(
    tmp_path: Path,
) -> None:
    project = Project(name="Quality fixture", part=PartContext(part_type="flat plate"))
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repository, store)
    session = capture.start(plan)
    frame = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=_encode(_good_image()),
        camera=CameraMetadata(width_px=640, height_px=480),
        media_type="image/png",
        extension=".png",
    )

    before = CanonicalContractBuilder.capture_package(project, capture.get(session.session_id))
    quality = CaptureQualityService(repository, store, OpenCvCaptureQualityAnalyzer())
    result = quality.analyze_clean_reference(session.session_id, view=CaptureViewType.FRONT)
    restored = capture.get(session.session_id)
    after = CanonicalContractBuilder.capture_package(project, restored)

    assert result.source_frame_id == frame.frame_id
    assert result.verdict is CaptureQualityVerdict.ACCEPT
    assert restored.quality_analyses == [result]
    assert before == after
    assert store.get_bytes(frame.artifact) == _encode(_good_image())

    # Persistence is idempotent for the same immutable source frame.
    assert quality.analyze_clean_reference(session.session_id, view=CaptureViewType.FRONT) == result
    assert len(capture.get(session.session_id).quality_analyses) == 1


def test_invalid_image_fails_explicitly() -> None:
    analyzer = OpenCvCaptureQualityAnalyzer()
    with pytest.raises(CaptureQualityError, match="could not be decoded"):
        analyzer.analyze(
            b"not-an-image",
            source_frame_id=FRAME_ID,
            view=CaptureViewType.FRONT,
        )
