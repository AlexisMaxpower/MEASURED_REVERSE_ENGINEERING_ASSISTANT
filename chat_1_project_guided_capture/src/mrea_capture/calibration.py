from __future__ import annotations

from math import sqrt
from typing import Protocol
from uuid import UUID

from .artifacts import ArtifactStore
from .models import CalibrationResult, CaptureViewType, FrameKind, MeasurementMatProfile
from .repositories import CaptureSessionRepository


class CalibrationDetectionError(RuntimeError):
    pass


class CalibrationDetector(Protocol):
    def detect(
        self,
        image_bytes: bytes,
        *,
        profile: MeasurementMatProfile,
        view: CaptureViewType,
        source_frame_id: UUID,
    ) -> CalibrationResult: ...


class OpenCvCharucoCalibrationDetector:
    """Detect ChArUco control points and map source image pixels to MAT_XY_MM."""

    def detect(
        self,
        image_bytes: bytes,
        *,
        profile: MeasurementMatProfile,
        view: CaptureViewType,
        source_frame_id: UUID,
    ) -> CalibrationResult:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise CalibrationDetectionError(
                "OpenCV vision dependencies are not installed"
            ) from exc

        if not hasattr(cv2, "aruco") or not hasattr(cv2.aruco, "CharucoDetector"):
            raise CalibrationDetectionError("OpenCV build lacks CharucoDetector support")

        dictionary_id = getattr(cv2.aruco, profile.dictionary_name, None)
        if dictionary_id is None:
            raise CalibrationDetectionError(
                f"unknown OpenCV ArUco dictionary: {profile.dictionary_name}"
            )

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise CalibrationDetectionError("image bytes could not be decoded")

        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        board = cv2.aruco.CharucoBoard(
            (profile.squares_x, profile.squares_y),
            profile.square_length_mm,
            profile.marker_length_mm,
            dictionary,
        )
        detector_parameters = cv2.aruco.DetectorParameters()
        detector_parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
        detector = cv2.aruco.CharucoDetector(
            board,
            cv2.aruco.CharucoParameters(),
            detector_parameters,
        )
        charuco_corners, charuco_ids, _, marker_ids = detector.detectBoard(image)

        corner_count = 0 if charuco_ids is None else len(charuco_ids)
        marker_count = 0 if marker_ids is None else len(marker_ids)
        if corner_count < 4:
            raise CalibrationDetectionError(
                f"at least 4 ChArUco corners are required, detected {corner_count}"
            )

        ids = charuco_ids.reshape(-1).astype(int)
        image_points = charuco_corners.reshape(-1, 2).astype("float64")
        board_points = board.getChessboardCorners()[ids, :2].astype("float64")
        homography, inlier_mask = cv2.findHomography(
            image_points,
            board_points,
            cv2.RANSAC,
            profile.ransac_reprojection_threshold_mm,
        )
        if homography is None or inlier_mask is None:
            raise CalibrationDetectionError("homography estimation failed")

        projected = cv2.perspectiveTransform(
            image_points.reshape(-1, 1, 2), homography
        ).reshape(-1, 2)
        inliers = inlier_mask.reshape(-1).astype(bool)
        if not inliers.any():
            raise CalibrationDetectionError("homography has no inlier control points")
        squared_error = ((projected[inliers] - board_points[inliers]) ** 2).sum(axis=1)
        rmse_mm = sqrt(float(squared_error.mean()))

        return CalibrationResult(
            view=view,
            source_frame_id=source_frame_id,
            mat_id=profile.mat_id,
            homography=[float(value) for value in homography.reshape(-1)],
            detected_marker_count=marker_count,
            detected_charuco_corner_count=corner_count,
            charuco_corner_ids=[int(value) for value in ids.tolist()],
            reprojection_rmse_mm=rmse_mm,
            quality=None,
        )


class CalibrationService:
    def __init__(
        self,
        repository: CaptureSessionRepository,
        artifact_store: ArtifactStore,
        detector: CalibrationDetector,
    ) -> None:
        self._repository = repository
        self._artifact_store = artifact_store
        self._detector = detector

    def calibrate_view(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        profile: MeasurementMatProfile,
    ) -> CalibrationResult:
        session = self._repository.get(session_id)
        if any(item.view is view for item in session.calibrations):
            raise CalibrationDetectionError(f"calibration already exists for view {view.value}")
        clean_frames = [
            frame
            for frame in session.frames
            if frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE
        ]
        if len(clean_frames) != 1:
            raise CalibrationDetectionError(
                f"view {view.value} requires exactly one clean reference frame"
            )
        clean = clean_frames[0]
        result = self._detector.detect(
            self._artifact_store.get_bytes(clean.artifact),
            profile=profile,
            view=view,
            source_frame_id=clean.frame_id,
        )
        session.calibrations.append(result)
        self._repository.save(session)
        return result
