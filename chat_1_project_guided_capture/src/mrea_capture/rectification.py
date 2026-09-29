from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .artifacts import ArtifactStore
from .models import (
    CalibrationResult,
    CaptureViewType,
    FrameKind,
    MeasurementMatProfile,
    RectifiedReferenceRecord,
)
from .repositories import CaptureSessionRepository


class RectificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RectifiedRaster:
    image_bytes: bytes
    width_px: int
    height_px: int
    media_type: str = "image/png"
    extension: str = ".png"


class PerspectiveNormalizer(Protocol):
    def normalize(
        self,
        image_bytes: bytes,
        *,
        calibration: CalibrationResult,
        profile: MeasurementMatProfile,
        pixels_per_mm: float,
    ) -> RectifiedRaster: ...


class OpenCvPerspectiveNormalizer:
    """Warp a clean reference into deterministic MAT_XY_MM raster space."""

    def normalize(
        self,
        image_bytes: bytes,
        *,
        calibration: CalibrationResult,
        profile: MeasurementMatProfile,
        pixels_per_mm: float,
    ) -> RectifiedRaster:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RectificationError("OpenCV vision dependencies are not installed") from exc

        if pixels_per_mm <= 0:
            raise RectificationError("pixels_per_mm must be greater than zero")
        if calibration.coordinate_system != "MAT_XY_MM":
            raise RectificationError("calibration coordinate system must be MAT_XY_MM")
        if calibration.mat_id != profile.mat_id:
            raise RectificationError("measurement mat profile does not match calibration mat_id")

        homography = np.asarray(calibration.homography, dtype=np.float64).reshape(3, 3)
        if not np.isfinite(homography).all():
            raise RectificationError("homography contains non-finite values")
        if np.linalg.matrix_rank(homography) < 3:
            raise RectificationError("homography is singular")

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise RectificationError("source image bytes could not be decoded")

        width_mm = profile.squares_x * profile.square_length_mm
        height_mm = profile.squares_y * profile.square_length_mm
        width_px = int(round(width_mm * pixels_per_mm))
        height_px = int(round(height_mm * pixels_per_mm))
        if width_px <= 0 or height_px <= 0:
            raise RectificationError("rectified raster dimensions are invalid")

        scale = np.array(
            [[pixels_per_mm, 0.0, 0.0], [0.0, pixels_per_mm, 0.0], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
        source_to_raster = scale @ homography
        border_value = 255 if image.ndim == 2 else tuple([255] * image.shape[2])
        rectified = cv2.warpPerspective(
            image,
            source_to_raster,
            (width_px, height_px),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=border_value,
        )
        ok, encoded_rectified = cv2.imencode(
            ".png",
            rectified,
            [cv2.IMWRITE_PNG_COMPRESSION, 3],
        )
        if not ok:
            raise RectificationError("rectified image could not be encoded")

        return RectifiedRaster(
            image_bytes=encoded_rectified.tobytes(),
            width_px=width_px,
            height_px=height_px,
        )


class RectificationService:
    def __init__(
        self,
        repository: CaptureSessionRepository,
        artifact_store: ArtifactStore,
        normalizer: PerspectiveNormalizer,
    ) -> None:
        self._repository = repository
        self._artifact_store = artifact_store
        self._normalizer = normalizer

    def rectify_view(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        profile: MeasurementMatProfile,
        pixels_per_mm: float = 10.0,
    ) -> RectifiedReferenceRecord:
        session = self._repository.get(session_id)
        if any(item.view is view for item in session.rectified_references):
            raise RectificationError(f"rectified reference already exists for view {view.value}")

        clean_frames = [
            frame
            for frame in session.frames
            if frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE
        ]
        if len(clean_frames) != 1:
            raise RectificationError(
                f"view {view.value} requires exactly one clean reference frame"
            )
        clean = clean_frames[0]

        calibrations = [item for item in session.calibrations if item.view is view]
        if len(calibrations) != 1:
            raise RectificationError(
                f"view {view.value} requires exactly one calibration result"
            )
        calibration = calibrations[0]
        if calibration.source_frame_id != clean.frame_id:
            raise RectificationError("calibration does not reference the clean source frame")
        if calibration.mat_id != profile.mat_id:
            raise RectificationError("measurement mat profile does not match stored calibration")

        raster = self._normalizer.normalize(
            self._artifact_store.get_bytes(clean.artifact),
            calibration=calibration,
            profile=profile,
            pixels_per_mm=pixels_per_mm,
        )
        artifact = self._artifact_store.put_bytes(
            raster.image_bytes,
            media_type=raster.media_type,
            extension=raster.extension,
        )
        record = RectifiedReferenceRecord(
            view=view,
            source_frame_id=clean.frame_id,
            calibration_id=calibration.calibration_id,
            mat_id=calibration.mat_id,
            artifact=artifact,
            pixels_per_mm=pixels_per_mm,
            width_px=raster.width_px,
            height_px=raster.height_px,
        )
        session.rectified_references.append(record)
        self._repository.save(session)
        return record
