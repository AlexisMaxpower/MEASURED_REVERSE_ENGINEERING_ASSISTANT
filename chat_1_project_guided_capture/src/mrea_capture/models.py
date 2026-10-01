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


class VoiceCaptureCommand(StrEnum):
    CAPTURE_MEASUREMENT_FRAME = "CAPTURE_MEASUREMENT_FRAME"


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


class VoiceCaptureEvent(StrictModel):
    """Attributable provenance for a voice command that triggered image capture."""

    voice_event_id: UUID = Field(default_factory=uuid4)
    command: VoiceCaptureCommand = VoiceCaptureCommand.CAPTURE_MEASUREMENT_FRAME
    triggered_at: datetime = Field(default_factory=utc_now)
    transcript: NonBlank | None = None
    locale: NonBlank | None = None

    @model_validator(mode="after")
    def validate_triggered_at(self) -> "VoiceCaptureEvent":
        if self.triggered_at.tzinfo is None:
            raise ValueError("voice trigger timestamp must be timezone-aware")
        return self


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
    source_clean_reference_frame_id: UUID | None = None
    supersedes_frame_id: UUID | None = None
    voice_event: VoiceCaptureEvent | None = None

    @model_validator(mode="after")
    def validate_frame_lineage_fields(self) -> "FrameRecord":
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.kind is FrameKind.CLEAN_REFERENCE and self.source_clean_reference_frame_id is not None:
            raise ValueError("clean reference cannot point to source_clean_reference_frame_id")
        if self.kind is FrameKind.CLEAN_REFERENCE and self.voice_event is not None:
            raise ValueError("voice capture event may only be attached to a measurement frame")
        if self.kind is FrameKind.MEASUREMENT and self.supersedes_frame_id is not None:
            raise ValueError("measurement frame cannot supersede another frame")
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

class CaptureQualityVerdict(StrEnum):
    ACCEPT = "ACCEPT"
    WARN = "WARN"
    REJECT = "REJECT"


class QualitySeverity(StrEnum):
    WARN = "WARN"
    REJECT = "REJECT"


class QualityReasonCode(StrEnum):
    BLUR = "BLUR"
    UNDEREXPOSED = "UNDEREXPOSED"
    OVEREXPOSED = "OVEREXPOSED"
    DARK_CLIPPING = "DARK_CLIPPING"
    BRIGHT_CLIPPING = "BRIGHT_CLIPPING"
    GLARE_RISK = "GLARE_RISK"
    LOW_SCENE_DETAIL = "LOW_SCENE_DETAIL"
    FRAMING_BORDER_ACTIVITY = "FRAMING_BORDER_ACTIVITY"
    LOW_MARKER_VISIBILITY = "LOW_MARKER_VISIBILITY"


class CaptureQualityMetrics(StrictModel):
    laplacian_variance: float = Field(ge=0)
    mean_luma: float = Field(ge=0, le=255)
    dark_clipped_fraction: float = Field(ge=0, le=1)
    bright_clipped_fraction: float = Field(ge=0, le=1)
    glare_proxy_fraction: float = Field(ge=0, le=1)
    edge_density: float = Field(ge=0, le=1)
    border_edge_ratio: float = Field(ge=0, le=1)
    marker_corner_visibility: float | None = Field(default=None, ge=0, le=1)


class CaptureQualityFinding(StrictModel):
    code: QualityReasonCode
    severity: QualitySeverity
    metric: NonBlank
    observed: float
    threshold: float
    comparison: NonBlank


class CaptureQualityResult(StrictModel):
    analysis_id: UUID
    source_frame_id: UUID
    view: CaptureViewType
    calibration_id: UUID | None = None
    mat_id: NonBlank | None = None
    policy_version: NonBlank
    verdict: CaptureQualityVerdict
    metrics: CaptureQualityMetrics
    findings: list[CaptureQualityFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_verdict(self) -> "CaptureQualityResult":
        has_reject = any(item.severity is QualitySeverity.REJECT for item in self.findings)
        has_warn = any(item.severity is QualitySeverity.WARN for item in self.findings)
        expected = (
            CaptureQualityVerdict.REJECT
            if has_reject
            else CaptureQualityVerdict.WARN
            if has_warn
            else CaptureQualityVerdict.ACCEPT
        )
        if self.verdict is not expected:
            raise ValueError("quality verdict must match finding severities")
        return self


class CaptureViewRevisionEvent(StrictModel):
    revision_id: UUID = Field(default_factory=uuid4)
    view: CaptureViewType
    reason: NonBlank
    reopened_at: datetime = Field(default_factory=utc_now)
    previous_accepted_at: datetime
    active_clean_reference_frame_id: UUID

    @model_validator(mode="after")
    def validate_revision_event(self) -> "CaptureViewRevisionEvent":
        if self.reopened_at.tzinfo is None or self.previous_accepted_at.tzinfo is None:
            raise ValueError("revision timestamps must be timezone-aware")
        if self.reopened_at < self.previous_accepted_at:
            raise ValueError("reopened_at cannot be earlier than previous_accepted_at")
        return self


class CaptureViewProgress(StrictModel):
    view: CaptureViewType
    required: bool = True
    status: CaptureViewStatus = CaptureViewStatus.PLANNED
    started_at: datetime | None = None
    captured_at: datetime | None = None
    accepted_at: datetime | None = None
    active_clean_reference_frame_id: UUID | None = None
    recapture_required: bool = False


class CaptureSession(StrictModel):
    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    plan_id: UUID
    views: list[CaptureViewProgress]
    frames: list[FrameRecord] = Field(default_factory=list)
    calibrations: list[CalibrationResult] = Field(default_factory=list)
    rectified_references: list[RectifiedReferenceRecord] = Field(default_factory=list)
    quality_analyses: list[CaptureQualityResult] = Field(default_factory=list)
    revision_events: list[CaptureViewRevisionEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_views_and_lineage(self) -> "CaptureSession":
        if not self.views:
            raise ValueError("capture session must contain at least one view")
        values = [item.view for item in self.views]
        if len(values) != len(set(values)):
            raise ValueError("capture session cannot contain duplicate views")

        frames_by_id = {frame.frame_id: frame for frame in self.frames}
        if len(frames_by_id) != len(self.frames):
            raise ValueError("capture session cannot contain duplicate frame ids")
        voice_event_ids = [
            frame.voice_event.voice_event_id
            for frame in self.frames
            if frame.voice_event is not None
        ]
        if len(voice_event_ids) != len(set(voice_event_ids)):
            raise ValueError("capture session cannot contain duplicate voice event ids")

        progress_by_view = {item.view: item for item in self.views}
        clean_by_view: dict[CaptureViewType, list[FrameRecord]] = {view: [] for view in values}
        for frame in self.frames:
            if frame.view not in progress_by_view:
                raise ValueError("frame view must belong to capture session")
            if frame.kind is FrameKind.CLEAN_REFERENCE:
                clean_by_view[frame.view].append(frame)

        # Backward-compatible migration: legacy sessions had exactly one clean frame per view
        # and measurement frames did not carry their clean-reference provenance explicitly.
        for progress in self.views:
            clean_frames = clean_by_view[progress.view]
            if progress.active_clean_reference_frame_id is None and len(clean_frames) == 1:
                object.__setattr__(progress, "active_clean_reference_frame_id", clean_frames[0].frame_id)
            if progress.active_clean_reference_frame_id is None and len(clean_frames) > 1:
                raise ValueError("multiple clean references require an explicit active clean frame")

            active_id = progress.active_clean_reference_frame_id
            if active_id is not None:
                active = frames_by_id.get(active_id)
                if active is None or active.kind is not FrameKind.CLEAN_REFERENCE or active.view is not progress.view:
                    raise ValueError("active clean reference must reference a clean frame in the same view")

        superseded_by: dict[UUID, UUID] = {}
        for frame in self.frames:
            if frame.kind is FrameKind.CLEAN_REFERENCE and frame.supersedes_frame_id is not None:
                predecessor = frames_by_id.get(frame.supersedes_frame_id)
                if predecessor is None or predecessor.kind is not FrameKind.CLEAN_REFERENCE:
                    raise ValueError("superseded frame must reference an existing clean reference")
                if predecessor.view is not frame.view:
                    raise ValueError("clean-reference supersession must stay within one view")
                if predecessor.frame_id == frame.frame_id:
                    raise ValueError("clean reference cannot supersede itself")
                if predecessor.frame_id in superseded_by:
                    raise ValueError("clean-reference lineage cannot branch")
                superseded_by[predecessor.frame_id] = frame.frame_id

        for progress in self.views:
            active_id = progress.active_clean_reference_frame_id
            if active_id is not None and active_id in superseded_by:
                raise ValueError("active clean reference must be the latest lineage frame")

        for frame in self.frames:
            if frame.kind is not FrameKind.MEASUREMENT:
                continue
            progress = progress_by_view[frame.view]
            if frame.source_clean_reference_frame_id is None:
                if progress.active_clean_reference_frame_id is None:
                    raise ValueError("measurement frame requires clean-reference provenance")
                object.__setattr__(
                    frame,
                    "source_clean_reference_frame_id",
                    progress.active_clean_reference_frame_id,
                )
            source = frames_by_id.get(frame.source_clean_reference_frame_id)
            if source is None or source.kind is not FrameKind.CLEAN_REFERENCE or source.view is not frame.view:
                raise ValueError("measurement source must be a clean reference in the same view")

        calibration_sources = [item.source_frame_id for item in self.calibrations]
        if len(calibration_sources) != len(set(calibration_sources)):
            raise ValueError("capture session cannot contain duplicate calibrations per clean frame")
        calibrations_by_id = {item.calibration_id: item for item in self.calibrations}
        if len(calibrations_by_id) != len(self.calibrations):
            raise ValueError("capture session cannot contain duplicate calibration ids")
        for item in self.calibrations:
            source = frames_by_id.get(item.source_frame_id)
            if source is None or source.kind is not FrameKind.CLEAN_REFERENCE:
                raise ValueError("calibration must reference a clean frame in the capture session")
            if source.view is not item.view:
                raise ValueError("calibration view must match its source frame")

        rectified_sources = [item.source_frame_id for item in self.rectified_references]
        if len(rectified_sources) != len(set(rectified_sources)):
            raise ValueError("capture session cannot contain duplicate rectified references per clean frame")
        for item in self.rectified_references:
            source = frames_by_id.get(item.source_frame_id)
            if source is None or source.kind is not FrameKind.CLEAN_REFERENCE:
                raise ValueError("rectified reference must reference a clean frame in the capture session")
            if source.view is not item.view:
                raise ValueError("rectified-reference view must match its source frame")
            calibration = calibrations_by_id.get(item.calibration_id)
            if calibration is None or calibration.source_frame_id != item.source_frame_id:
                raise ValueError("rectified reference must use calibration from the same clean frame")

        quality_sources = [item.source_frame_id for item in self.quality_analyses]
        if len(quality_sources) != len(set(quality_sources)):
            raise ValueError("capture session cannot contain duplicate quality analyses per frame")
        for item in self.quality_analyses:
            source = frames_by_id.get(item.source_frame_id)
            if source is None or source.kind is not FrameKind.CLEAN_REFERENCE:
                raise ValueError("quality analysis must reference a clean frame in the capture session")
            if source.view is not item.view:
                raise ValueError("quality analysis view must match its source frame")
            if item.calibration_id is not None:
                calibration = calibrations_by_id.get(item.calibration_id)
                if calibration is None or calibration.source_frame_id != item.source_frame_id:
                    raise ValueError("quality calibration must belong to the same clean frame")

        revision_ids = [item.revision_id for item in self.revision_events]
        if len(revision_ids) != len(set(revision_ids)):
            raise ValueError("capture session cannot contain duplicate revision ids")
        for event in self.revision_events:
            progress = progress_by_view.get(event.view)
            if progress is None:
                raise ValueError("revision event view must belong to capture session")
            source = frames_by_id.get(event.active_clean_reference_frame_id)
            if source is None or source.kind is not FrameKind.CLEAN_REFERENCE or source.view is not event.view:
                raise ValueError("revision event must reference a clean frame in the same view")

        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        return self