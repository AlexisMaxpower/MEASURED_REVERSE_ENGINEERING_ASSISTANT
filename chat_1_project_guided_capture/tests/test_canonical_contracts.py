import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import CameraMetadata, CaptureViewType, PartContext, Project
from mrea_capture.repositories import JsonCaptureSessionRepository, JsonProjectRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


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


def _camera() -> CameraMetadata:
    return CameraMetadata(width_px=1604, height_px=842, device_model="Test Phone")


def test_project_and_front_capture_package_are_canonical(tmp_path: Path) -> None:
    project = Project(
        name="Golden flat plate",
        part=PartContext(part_type="flat replacement plate"),
    )
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    service = CaptureSessionService(
        JsonCaptureSessionRepository(tmp_path),
        FileSystemArtifactStore(tmp_path),
    )
    session = service.start(plan)
    service.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"clean",
        camera=_camera(),
        captured_at=datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc),
        media_type="image/png",
        extension=".png",
    )
    service.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"measurement",
        camera=_camera(),
        captured_at=datetime(2026, 9, 29, 15, 1, tzinfo=timezone.utc),
        media_type="image/png",
        extension=".png",
    )
    session = service.accept_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        accepted_at=datetime(2026, 9, 29, 15, 2, tzinfo=timezone.utc),
    )

    project_contract = CanonicalContractBuilder.project_contract(project)
    capture_package = CanonicalContractBuilder.capture_package(project, session)

    _validator("ProjectContract").validate(project_contract)
    _validator("CapturePackage").validate(capture_package)
    assert capture_package["project_id"] == project_contract["project_id"]
    assert capture_package["part_id"] == project_contract["part_id"]
    assert capture_package["views"][0]["view_type"] == "FRONT"
    assert len(capture_package["views"][0]["measurement_frames"]) == 1
    assert CanonicalContractBuilder.capture_package(project, session) == capture_package


def test_legacy_project_without_part_id_gets_stable_id(tmp_path: Path) -> None:
    project_id = uuid4()
    path = tmp_path / "projects" / f"{project_id}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "project_id": str(project_id),
                "name": "legacy",
                "part": {"part_type": "plate"},
                "status": "ACTIVE",
                "created_at": "2026-09-29T15:00:00Z",
                "updated_at": "2026-09-29T15:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    repository = JsonProjectRepository(tmp_path)

    first = repository.get(project_id)
    second = repository.get(project_id)

    assert first.part_id == second.part_id
