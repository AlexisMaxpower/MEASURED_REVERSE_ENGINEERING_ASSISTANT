from datetime import datetime, timezone
from pathlib import Path

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.models import (
    CameraMetadata,
    CaptureViewStatus,
    CaptureViewType,
    FrameKind,
    PartContext,
    Project,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import (
    CapturePlanService,
    CaptureSessionService,
    CaptureWorkflowError,
)


def build_service(tmp_path: Path, views=None):
    project = Project(name="P001", part=PartContext(part_type="flat bracket"))
    plan = CapturePlanService().create_plan(project, views=views)
    artifacts = FileSystemArtifactStore(tmp_path)
    service = CaptureSessionService(JsonCaptureSessionRepository(tmp_path), artifacts)
    return service, artifacts, service.start(plan)


def camera() -> CameraMetadata:
    return CameraMetadata(
        width_px=4000,
        height_px=3000,
        device_model="Test Phone",
        rotation_degrees=0,
        focal_length_mm=6.7,
        iso=100,
        exposure_time_us=8000,
    )


def test_artifact_store_roundtrip_and_checksum(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    payload = b"fake-jpeg-content"

    artifact = store.put_bytes(payload, media_type="image/jpeg", extension="jpg")

    assert artifact.size_bytes == len(payload)
    assert len(artifact.sha256) == 64
    assert store.get_bytes(artifact) == payload


def test_measurement_frame_requires_clean_reference(tmp_path: Path) -> None:
    service, _, session = build_service(tmp_path)

    with pytest.raises(CaptureWorkflowError, match="requires clean reference"):
        service.capture_measurement_frame(
            session.session_id,
            view=CaptureViewType.FRONT,
            image_bytes=b"measurement",
            camera=camera(),
        )


def test_clean_reference_and_measurement_frames_remain_distinct(tmp_path: Path) -> None:
    service, artifacts, session = build_service(tmp_path)
    clean_time = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    measurement_time = datetime(2026, 9, 29, 12, 1, tzinfo=timezone.utc)

    clean = service.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-image",
        camera=camera(),
        captured_at=clean_time,
    )
    measurement = service.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement-image",
        camera=camera(),
        captured_at=measurement_time,
    )
    restored = service.get(session.session_id)

    assert clean.kind is FrameKind.CLEAN_REFERENCE
    assert measurement.kind is FrameKind.MEASUREMENT
    assert clean.frame_id != measurement.frame_id
    assert clean.artifact.sha256 != measurement.artifact.sha256
    assert artifacts.get_bytes(clean.artifact) == b"clean-image"
    assert artifacts.get_bytes(measurement.artifact) == b"measurement-image"
    assert restored.frames == [clean, measurement]
    assert restored.frames[0].camera.device_model == "Test Phone"
    assert restored.frames[0].captured_at == clean_time


def test_accepting_required_front_completes_session(tmp_path: Path) -> None:
    service, _, session = build_service(
        tmp_path,
        views=[CaptureViewType.FRONT, CaptureViewType.OPTIONAL_3Q],
    )
    service.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-image",
        camera=camera(),
    )

    accepted = service.accept_view(session.session_id, view=CaptureViewType.FRONT)

    front = next(item for item in accepted.views if item.view is CaptureViewType.FRONT)
    optional = next(item for item in accepted.views if item.view is CaptureViewType.OPTIONAL_3Q)
    assert front.status is CaptureViewStatus.ACCEPTED
    assert optional.status is CaptureViewStatus.PLANNED
    assert optional.required is False
    assert accepted.completed_at is not None
