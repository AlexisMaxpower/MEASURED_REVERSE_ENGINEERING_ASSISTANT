import json
from pathlib import Path

import cv2
from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.calibration import CalibrationService, OpenCvCharucoCalibrationDetector
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CameraMetadata,
    CaptureViewType,
    MeasurementMatProfile,
    PartContext,
    Project,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


def _validator(name: str) -> Draft202012Validator:
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
            "$ref": f"#/$defs/{name}",
        },
        format_checker=FormatChecker(),
    )


def test_synthetic_charuco_calibration_populates_canonical_capture_package(
    tmp_path: Path,
) -> None:
    profile = MeasurementMatProfile(
        mat_id="MAT-A4-V1",
        squares_x=5,
        squares_y=7,
        square_length_mm=20.0,
        marker_length_mm=14.0,
    )
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard((5, 7), 20.0, 14.0, dictionary)
    image = board.generateImage((1000, 1400), marginSize=50)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    project = Project(
        name="Calibration fixture",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repository, store)
    session = capture.start(plan)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=encoded.tobytes(),
        camera=CameraMetadata(width_px=1000, height_px=1400),
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
    restored = capture.get(session.session_id)
    package = CanonicalContractBuilder.capture_package(project, restored)

    assert calibration.detected_charuco_corner_count == 24
    assert calibration.detected_marker_count > 0
    assert len(calibration.homography) == 9
    assert calibration.reprojection_rmse_mm < 1e-3
    assert package["views"][0]["calibration"]["coordinate_system"] == "MAT_XY_MM"
    assert package["views"][0]["calibration"]["mat_id"] == "MAT-A4-V1"
    assert package["views"][0]["calibration"]["quality"] is None
    _validator("CapturePackage").validate(package)
