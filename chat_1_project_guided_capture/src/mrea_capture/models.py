from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class CaptureViewType(StrEnum):
    FRONT = "FRONT"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    REAR = "REAR"
    DETAIL_A = "DETAIL_A"
    DETAIL_B = "DETAIL_B"
    OPTIONAL_3Q = "OPTIONAL_3Q"


class CaptureViewStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    CAPTURED = "CAPTURED"
    ACCEPTED = "ACCEPTED"


class FrameKind(StrEnum):
    CLEAN_REFERENCE = "CLEAN_REFERENCE"
    MEASUREMENT = "MEASUREMENT"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PartContext(StrictModel):
    part_type: NonBlank
    equipment: NonBlank | None = None
    assembly: NonBlank | None = None
    purpose: NonBlank | None = None
    problem: NonBlank | None = None
    reverse_engineering_reason: NonBlank | None = None
    original_material: NonBlank | None = None
    original_manufacturing_method: NonBlank | None = None
    target_manufacturing_method: NonBlank | None = None
    failure_photo_artifact_ids: list[NonBlank] = Field(default_factory=list)
    comments: str | None = None


class Project(StrictModel):
    project_id: UUID = Field(default_factory=uuid4)
    part_id: UUID = Field(default_factory=uuid4)
    name: NonBlank
    part: PartContext
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def backfill_stable_part_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("part_id") and data.get("project_id"):
            migrated = dict(data)
            project_id = UUID(str(data["project_id"]))
            migrated["part_id"] = uuid5(NAMESPACE_URL, f"mrea:part:v1:{project_id}")
            return migrated
        return data

    @model_validator(mode="after")
    def validate_timestamps(self) -> "Project":
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("project timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self


class CapturePlanItem(StrictModel):
    sequence: int = Field(ge=1)
    view: CaptureViewType
    required: bool = True
    rationale: NonBlank


class CapturePlan(StrictModel):
    project_id: UUID
    plan_id: UUID = Field(default_factory=uuid4)
    internal_schema_version: str = "chat1.capture-plan.v1"
    items: list[CapturePlanItem]
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_items(self) -> "CapturePlan":
        if not self.items:
            raise ValueError("capture plan must contain at least one view")
        sequences = [item.sequence for item in self.items]
        if sequences != list(range(1, len(self.items) + 1)):
            raise ValueError("capture plan sequences must be contiguous and start at 1")
        views = [item.view for item in self.items]
        if len(views) != len(set(views)):
            raise ValueError("capture plan cannot contain duplicate views")
        return self


class CameraMetadata(StrictModel):
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    device_model: NonBlank | None = None
    rotation_degrees: int = Field(default=0, ge=0, lt=360)
    focal_length_mm: float | None = Field(default=None, gt=0)
    iso: int | None = Field(default=None, gt=0)
    exposure_time_us: int | None = Field(default=None, gt=0)


class ArtifactRecord(StrictModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    relative_path: NonBlank
    media_type: NonBlank
    size_bytes: int = Field(ge=0)
    sha256: Sha256Hex
    created_at: datetime = Field(default_factory=utc_now)


class FrameRecord(StrictModel):
    frame_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    session_id: UUID
    view: CaptureViewType
    kind: FrameKind
    artifact: ArtifactRecord
    captured_at: datetime = Field(default_factory=utc_now)
    camera: CameraMetadata

    @model_validator(mode="after")
    def validate_timestamp(self) -> "FrameRecord":
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        return self


class MeasurementMatProfile(StrictModel):
    mat_id: NonBlank
    dictionary_name: NonBlank = "DICT_4X4_50"
    squares_x: int = Field(ge=3)
    squares_y: int = Field(ge=3)
    square_length_mm: float = Field(gt=0)
    marker_length_mm: float = Field(gt=0)
    ransac_reprojection_threshold_mm: float = Field(default=0.5, gt=0)

    @model_validator(mode="after")
    def validate_marker_size(self) -> "MeasurementMatProfile":
        if self.marker_length_mm >= self.square_length_mm:
            raise ValueError("marker_length_mm must be smaller than square_length_mm")
        return self


class CalibrationResult(StrictModel):
    calibration_id: UUID
    view: CaptureViewType
    source_frame_id: UUID
    mat_id: NonBlank
    coordinate_system: str = "MAT_XY_MM"
    homography: list[float] = Field(min_length=9, max_length=9)
    detected_marker_count: int = Field(ge=0)
    detected_charuco_corner_count: int = Field(ge=0)
    charuco_corner_ids: list[int] = Field(default_factory=list)
    reprojection_rmse_mm: float = Field(ge=0)
    quality: float | None = Field(default=None, ge=0, le=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def backfill_stable_calibration_id(cls, data: Any) -> Any:
        if (
            isinstance(data, dict)
            and not data.get("calibration_id")
            and data.get("source_frame_id")
            and data.get("mat_id")
        ):
            migrated = dict(data)
            migrated["calibration_id"] = uuid5(
                NAMESPACE_URL,
                f"mrea:calibration:v1:{data['source_frame_id']}:{data['mat_id']}",
            )
            return migrated
        return data

    @model_validator(mode="after")
    def validate_coordinate_system(self) -> "CalibrationResult":
        if self.coordinate_system != "MAT_XY_MM":
            raise ValueError("calibration coordinate system must be MAT_XY_MM")
        return self


class RectifiedReferenceRecord(StrictModel):
    rectified_reference_id: UUID = Field(default_factory=uuid4)
    view: CaptureViewType
    source_frame_id: UUID
    calibration_id: UUID
    mat_id: NonBlank
    artifact: ArtifactRecord
    coordinate_system: str = "MAT_XY_MM"
    pixels_per_mm: float = Field(gt=0)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_rectified_reference(self) -> "RectifiedReferenceRecord":
        if self.coordinate_system != "MAT_XY_MM":
            raise ValueError("rectified coordinate system must be MAT_XY_MM")
        if self.created_at.tzinfo is None:
            raise ValueError("rectified reference timestamp must be timezone-aware")
        return self


class CaptureViewProgress(StrictModel):
    view: CaptureViewType
    required: bool = True
    status: CaptureViewStatus = CaptureViewStatus.PLANNED
    started_at: datetime | None = None
    captured_at: datetime | None = None
    accepted_at: datetime | None = None


class CaptureSession(StrictModel):
    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    plan_id: UUID
    views: list[CaptureViewProgress]
    frames: list[FrameRecord] = Field(default_factory=list)
    calibrations: list[CalibrationResult] = Field(default_factory=list)
    rectified_references: list[RectifiedReferenceRecord] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_views(self) -> "CaptureSession":
        if not self.views:
            raise ValueError("capture session must contain at least one view")
        values = [item.view for item in self.views]
        if len(values) != len(set(values)):
            raise ValueError("capture session cannot contain duplicate views")
        calibration_views = [item.view for item in self.calibrations]
        if len(calibration_views) != len(set(calibration_views)):
            raise ValueError("capture session cannot contain duplicate calibrations per view")
        rectified_views = [item.view for item in self.rectified_references]
        if len(rectified_views) != len(set(rectified_views)):
            raise ValueError("capture session cannot contain duplicate rectified references per view")
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        return self
