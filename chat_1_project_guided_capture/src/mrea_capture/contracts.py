from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from .lineage import (
    active_clean_reference,
    calibration_for_active_reference,
    measurement_frames_for_active_reference,
)
from .models import ArtifactRecord, CaptureSession, CaptureViewType, FrameRecord, Project


class CanonicalContractError(ValueError):
    pass


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise CanonicalContractError("canonical timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _opaque(value: UUID) -> str:
    return str(value)


def _artifact_reference(
    artifact: ArtifactRecord,
    *,
    kind: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canonical_metadata: dict[str, Any] = {
        "relative_path": artifact.relative_path,
        "size_bytes": artifact.size_bytes,
    }
    if metadata:
        canonical_metadata.update(metadata)
    return {
        "artifact_id": _opaque(artifact.artifact_id),
        "kind": kind,
        "uri": f"mrea://artifact/{artifact.artifact_id}",
        "media_type": artifact.media_type,
        "sha256": artifact.sha256,
        "metadata": canonical_metadata,
    }


def _view_id(session: CaptureSession, view: CaptureViewType) -> str:
    return str(uuid5(NAMESPACE_URL, f"mrea:capture-view:v1:{session.session_id}:{view.value}"))


def _capture_package_id(session: CaptureSession) -> str:
    return str(uuid5(NAMESPACE_URL, f"mrea:capture-package:v1:{session.session_id}"))


class CanonicalContractBuilder:
    """Adapter from Chat 1 internal models to Integrator-owned v1 wire contracts."""

    @staticmethod
    def project_contract(project: Project) -> dict[str, Any]:
        return {
            "schema_version": "mrea.project.v1",
            "project_id": _opaque(project.project_id),
            "part_id": _opaque(project.part_id),
            "name": project.name,
            "status": project.status.value,
            "part": {
                "part_type": project.part.part_type,
                "equipment": project.part.equipment,
                "assembly": project.part.assembly,
                "purpose": project.part.purpose,
                "problem": project.part.problem,
                "reverse_engineering_reason": project.part.reverse_engineering_reason,
                "original_material": project.part.original_material,
                "original_manufacturing_method": project.part.original_manufacturing_method,
                "target_manufacturing_method": project.part.target_manufacturing_method,
                "comments": project.part.comments,
            },
            "created_at": _timestamp(project.created_at),
            "updated_at": _timestamp(project.updated_at),
        }

    @classmethod
    def capture_package(
        cls,
        project: Project,
        session: CaptureSession,
    ) -> dict[str, Any]:
        if session.project_id != project.project_id:
            raise CanonicalContractError("capture session belongs to a different project")

        views: list[dict[str, Any]] = []
        for progress in session.views:
            clean = active_clean_reference(session, progress.view)
            if clean is None:
                if progress.required:
                    raise CanonicalContractError(
                        f"required view {progress.view.value} has no active clean reference frame"
                    )
                continue

            view_id = _view_id(session, progress.view)
            measurements = [
                cls._measurement_capture_frame(frame, view_id=view_id)
                for frame in measurement_frames_for_active_reference(session, progress.view)
            ]
            calibration = calibration_for_active_reference(session, progress.view)
            canonical_calibration = None
            if calibration is not None:
                canonical_calibration = {
                    "coordinate_system": "MAT_XY_MM",
                    "mat_id": calibration.mat_id,
                    "homography": calibration.homography,
                    "quality": calibration.quality,
                }

            views.append(
                {
                    "view_id": view_id,
                    "view_type": progress.view.value,
                    "clean_reference_frame": _artifact_reference(
                        clean.artifact,
                        kind="CLEAN_REFERENCE_IMAGE",
                        metadata={
                            "width_px": clean.camera.width_px,
                            "height_px": clean.camera.height_px,
                        },
                    ),
                    "measurement_frames": measurements,
                    "calibration": canonical_calibration,
                }
            )

        if not views:
            raise CanonicalContractError("capture package must contain at least one captured view")

        return {
            "schema_version": "mrea.capture-package.v1",
            "capture_package_id": _capture_package_id(session),
            "project_id": _opaque(project.project_id),
            "part_id": _opaque(project.part_id),
            "views": views,
        }

    @staticmethod
    def _measurement_capture_frame(frame: FrameRecord, *, view_id: str) -> dict[str, Any]:
        voice_event = None
        if frame.voice_event is not None:
            voice_event = {
                "event_id": _opaque(frame.voice_event.voice_event_id),
                "command": frame.voice_event.command.value,
                "triggered_at": _timestamp(frame.voice_event.triggered_at),
            }
            if frame.voice_event.transcript is not None:
                voice_event["transcript"] = frame.voice_event.transcript
            if frame.voice_event.locale is not None:
                voice_event["locale"] = frame.voice_event.locale

        return {
            "frame_id": _opaque(frame.frame_id),
            "view_id": view_id,
            "artifact": _artifact_reference(
                frame.artifact,
                kind="MEASUREMENT_FRAME_IMAGE",
                metadata={
                    "width_px": frame.camera.width_px,
                    "height_px": frame.camera.height_px,
                },
            ),
            "captured_at": _timestamp(frame.captured_at),
            "camera_metadata": frame.camera.model_dump(mode="json", exclude_none=True),
            "voice_event": voice_event,
        }
