import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CameraMetadata,
    CaptureViewType,
    PartContext,
    Project,
    VoiceCaptureCommand,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService, CaptureWorkflowError


def _validator(name: str) -> Draft202012Validator:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "core"
        / "contracts"
        / "mrea_contracts_v1.schema.json"
    )
    root = json.loads(schema_path.read_text(encoding="utf-8"))
    schema = {
        "$schema": root["$schema"],
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{name}",
    }
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _fixture(tmp_path: Path):
    project = Project(name="Voice capture", part=PartContext(part_type="test part"))
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    repository = JsonCaptureSessionRepository(tmp_path)
    service = CaptureSessionService(repository, FileSystemArtifactStore(tmp_path))
    session = service.start(plan)
    clean = service.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean-reference",
        camera=CameraMetadata(width_px=1920, height_px=1080, device_model="Test Phone"),
        captured_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
    )
    return project, repository, service, session.session_id, clean


def test_voice_triggered_measurement_frame_persists_attributable_provenance_and_serializes(
    tmp_path: Path,
) -> None:
    project, _, service, session_id, clean = _fixture(tmp_path)
    trigger_time = datetime(2026, 10, 1, 15, 1, tzinfo=timezone(timedelta(hours=3)))
    capture_time = datetime(2026, 10, 1, 12, 1, 1, tzinfo=timezone.utc)

    frame = service.capture_measurement_frame_from_voice_trigger(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"voice-measurement-frame",
        camera=CameraMetadata(width_px=1920, height_px=1080, device_model="Test Phone"),
        transcript="снять кадр",
        locale="ru-RU",
        triggered_at=trigger_time,
        captured_at=capture_time,
    )
    restored = service.get(session_id)

    assert frame.source_clean_reference_frame_id == clean.frame_id
    assert frame.voice_event is not None
    assert frame.voice_event.command is VoiceCaptureCommand.CAPTURE_MEASUREMENT_FRAME
    assert frame.voice_event.transcript == "снять кадр"
    assert frame.voice_event.locale == "ru-RU"
    assert restored.frames[-1].voice_event == frame.voice_event

    package = CanonicalContractBuilder.capture_package(project, restored)
    _validator("CapturePackage").validate(package)
    canonical_frame = package["views"][0]["measurement_frames"][0]
    voice_event = canonical_frame["voice_event"]

    assert voice_event == {
        "event_id": str(frame.voice_event.voice_event_id),
        "command": "CAPTURE_MEASUREMENT_FRAME",
        "triggered_at": "2026-10-01T12:01:00Z",
        "transcript": "снять кадр",
        "locale": "ru-RU",
    }
    assert {"value", "unit", "measurement_id"}.isdisjoint(voice_event)


def test_manual_measurement_frame_remains_backward_compatible_with_null_voice_event(
    tmp_path: Path,
) -> None:
    project, _, service, session_id, _ = _fixture(tmp_path)
    frame = service.capture_measurement_frame(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"manual-measurement-frame",
        camera=CameraMetadata(width_px=1920, height_px=1080),
    )

    assert frame.voice_event is None
    package = CanonicalContractBuilder.capture_package(project, service.get(session_id))
    _validator("CapturePackage").validate(package)
    assert package["views"][0]["measurement_frames"][0]["voice_event"] is None


def test_recapture_keeps_historical_voice_evidence_but_canonical_package_uses_active_attempt(
    tmp_path: Path,
) -> None:
    project, _, service, session_id, first_clean = _fixture(tmp_path)
    old_frame = service.capture_measurement_frame_from_voice_trigger(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"old-voice-frame",
        camera=CameraMetadata(width_px=1920, height_px=1080),
        transcript="снять первый",
        triggered_at=datetime(2026, 10, 1, 12, 1, tzinfo=timezone.utc),
    )

    second_clean = service.recapture_clean_reference(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"second-clean-reference",
        camera=CameraMetadata(width_px=1920, height_px=1080),
        captured_at=datetime(2026, 10, 1, 12, 2, tzinfo=timezone.utc),
    )
    new_frame = service.capture_measurement_frame_from_voice_trigger(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"new-voice-frame",
        camera=CameraMetadata(width_px=1920, height_px=1080),
        transcript="снять второй",
        triggered_at=datetime(2026, 10, 1, 12, 3, tzinfo=timezone.utc),
    )

    restored = service.get(session_id)
    assert old_frame.source_clean_reference_frame_id == first_clean.frame_id
    assert new_frame.source_clean_reference_frame_id == second_clean.frame_id
    assert len([item for item in restored.frames if item.voice_event is not None]) == 2

    package = CanonicalContractBuilder.capture_package(project, restored)
    canonical_frames = package["views"][0]["measurement_frames"]
    assert [item["frame_id"] for item in canonical_frames] == [str(new_frame.frame_id)]
    assert canonical_frames[0]["voice_event"]["event_id"] == str(new_frame.voice_event.voice_event_id)


def test_voice_trigger_requires_existing_clean_reference_and_does_not_persist_orphan_event(
    tmp_path: Path,
) -> None:
    project = Project(name="No clean", part=PartContext(part_type="test part"))
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    service = CaptureSessionService(repository, FileSystemArtifactStore(tmp_path))
    session = service.start(plan)

    with pytest.raises(CaptureWorkflowError, match="requires clean reference"):
        service.capture_measurement_frame_from_voice_trigger(
            session.session_id,
            view=CaptureViewType.FRONT,
            image_bytes=b"orphan",
            camera=CameraMetadata(width_px=640, height_px=480),
            transcript="снять",
        )

    assert service.get(session.session_id).frames == []


def test_voice_trigger_rejects_naive_timestamp(tmp_path: Path) -> None:
    _, _, service, session_id, _ = _fixture(tmp_path)

    with pytest.raises(CaptureWorkflowError, match="timezone-aware"):
        service.capture_measurement_frame_from_voice_trigger(
            session_id,
            view=CaptureViewType.FRONT,
            image_bytes=b"measurement",
            camera=CameraMetadata(width_px=640, height_px=480),
            triggered_at=datetime(2026, 10, 1, 12, 1),
        )
