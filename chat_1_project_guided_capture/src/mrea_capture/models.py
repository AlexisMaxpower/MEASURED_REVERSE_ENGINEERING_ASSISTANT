from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
    name: NonBlank
    part: PartContext
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

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


class CaptureViewProgress(StrictModel):
    view: CaptureViewType
    status: CaptureViewStatus = CaptureViewStatus.PLANNED
    started_at: datetime | None = None
    captured_at: datetime | None = None
    accepted_at: datetime | None = None


class CaptureSession(StrictModel):
    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    plan_id: UUID
    views: list[CaptureViewProgress]
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_views(self) -> "CaptureSession":
        if not self.views:
            raise ValueError("capture session must contain at least one view")
        values = [item.view for item in self.views]
        if len(values) != len(set(values)):
            raise ValueError("capture session cannot contain duplicate views")
        return self
