import json
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest
from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.calibration import CalibrationService, OpenCvCharucoCalibrationDetector
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureViewType,
    MeasurementMatProfile,
    PartContext,
    Project,
)
from mrea_capture.rectification import (
    OpenCvPerspectiveNormalizer,
    RectificationError,
    RectificationService,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


def _capture_validator() -> Draft202012Validator:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "core"
        / "contracts"
        / "mrea_contracts_v1.schema.json"
    )
    root = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(
        {
            "$schema": root["$schema"],
            "$defs": root["$defs"],
            "$ref": "#/$defs/CapturePackage",
        },
        format_checker=FormatChecker(),
    )


def _profile() -> MeasurementMatProfile:
    return MeasurementMatProfile(
        mat_id="MAT-A4-V1",
        squares_x=5,
        squares_y=7,
        square_length_mm=20.0,
        marker_length_mm=14.0,
    )


def _perspective_fixture(profile: MeasurementMatProfile) -> tuple[np.ndarray, bytes]:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard(
        (profile.squares_x, profile.squares_y),
        profile.square_length_mm,
        profile.marker_length_mm,
        dictionary,
    )
    canonical = board.generateImage((1000, 1400), marginSize=0)
    src = np.float32([[0, 0], [999, 0], [999, 1399], [0, 1399]])
    dst = np.float32([[120, 90], [1080, 180], [1020, 1510], [180, 1450]])
    known_warp = cv2.getPerspectiveTransform(src, dst)
    distorted = cv2.warpPerspective(
        canonical,
        known_warp,
        (1200, 1600),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    ok, encoded = cv2.imencode(".png", distorted, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    assert ok
    return canonical, encoded.tobytes()


def test_rectification_preserves_original_and_records_provenance(tmp_path: Path) -> None:
    profile = _profile()
    canonical_image, distorted_bytes = _perspective_fixture(profile)

    project = Project(
        name="Perspective fixture",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repository, store)
    session = capture.start(plan)
    clean = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=distorted_bytes,
        camera=CameraMetadata(width_px=1200, height_px=1600),
        media_type="image/png",
        extension=".png",
    )

    calibration = CalibrationService(
        repository,
        store,
        OpenCvCharucoCalibrationDetector(),
    ).calibrate_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        profile=profile,
    )
    before = CanonicalContractBuilder.capture_package(project, capture.get(session.session_id))

    normalizer = OpenCvPerspectiveNormalizer()
    first_raster = normalizer.normalize(
        distorted_bytes,
        calibration=calibration,
        profile=profile,
        pixels_per_mm=10.0,
    )
    second_raster = normalizer.normalize(
        distorted_bytes,
        calibration=calibration,
        profile=profile,
        pixels_per_mm=10.0,
    )
    assert first_raster.image_bytes == second_raster.image_bytes

    rectified = RectificationService(repository, store, normalizer).rectify_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        profile=profile,
        pixels_per_mm=10.0,
    )
    restored = capture.get(session.session_id)
    after = CanonicalContractBuilder.capture_package(project, restored)

    assert store.get_bytes(clean.artifact) == distorted_bytes
    assert clean.artifact.artifact_id != rectified.artifact.artifact_id
    assert clean.artifact.sha256 != rectified.artifact.sha256
    assert rectified.source_frame_id == clean.frame_id
    assert rectified.calibration_id == calibration.calibration_id
    assert rectified.mat_id == profile.mat_id
    assert rectified.width_px == 1000
    assert rectified.height_px == 1400
    assert rectified.coordinate_system == "MAT_XY_MM"
    assert restored.rectified_references == [rectified]

    decoded = cv2.imdecode(
        np.frombuffer(store.get_bytes(rectified.artifact), dtype=np.uint8),
        cv2.IMREAD_GRAYSCALE,
    )
    assert decoded is not None
    assert decoded.shape == canonical_image.shape
    mean_absolute_error = float(
        np.mean(np.abs(decoded.astype(np.int16) - canonical_image.astype(np.int16)))
    )
    assert mean_absolute_error < 8.0

    assert after == before
    _capture_validator().validate(after)


def test_invalid_homography_fails_explicitly() -> None:
    calibration = CalibrationResult(
        view=CaptureViewType.FRONT,
        source_frame_id=uuid4(),
        mat_id="MAT-A4-V1",
        homography=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        detected_marker_count=1,
        detected_charuco_corner_count=4,
        charuco_corner_ids=[0, 1, 2, 3],
        reprojection_rmse_mm=0.0,
    )

    with pytest.raises(RectificationError, match="singular"):
        OpenCvPerspectiveNormalizer().normalize(
            b"not-used-because-homography-is-checked-after-decode",
            calibration=calibration,
            profile=_profile(),
            pixels_per_mm=10.0,
        )


def test_legacy_calibration_without_id_gets_stable_internal_identity() -> None:
    source_frame_id = uuid4()
    payload = {
        "view": "FRONT",
        "source_frame_id": str(source_frame_id),
        "mat_id": "MAT-A4-V1",
        "homography": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        "detected_marker_count": 4,
        "detected_charuco_corner_count": 4,
        "charuco_corner_ids": [0, 1, 2, 3],
        "reprojection_rmse_mm": 0.0,
    }

    first = CalibrationResult.model_validate(payload)
    second = CalibrationResult.model_validate(payload)

    assert first.calibration_id == second.calibration_id
