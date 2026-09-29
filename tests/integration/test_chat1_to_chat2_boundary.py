from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture import (
    CameraMetadata,
    CanonicalContractBuilder,
    CapturePlanService,
    CaptureSessionService,
    CaptureViewType,
    FileSystemArtifactStore,
    JsonCaptureSessionRepository,
    PartContext,
    Project,
)
from physical_measurement import (
    CanonicalMeasurementAdapter,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "core" / "contracts" / "mrea_contracts_v1.schema.json"


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-XSLICE12-{self._value:03d}"


def _validator(definition_name: str) -> Draft202012Validator:
    root = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(
        {
            "$schema": root["$schema"],
            "$defs": root["$defs"],
            "$ref": f"#/$defs/{definition_name}",
        },
        format_checker=FormatChecker(),
    )


def test_real_chat1_capture_package_is_consumed_by_chat2_without_rewriting_evidence_ids(
    tmp_path: Path,
) -> None:
    project = Project(
        name="Chat1 to Chat2 integration fixture",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    capture_repository = JsonCaptureSessionRepository(tmp_path / "capture-repository")
    artifact_store = FileSystemArtifactStore(tmp_path / "artifacts")
    capture_service = CaptureSessionService(capture_repository, artifact_store)
    session = capture_service.start(plan)

    clean = capture_service.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"chat1-clean-reference",
        camera=CameraMetadata(width_px=1200, height_px=800),
        media_type="image/png",
        extension=".png",
    )
    evidence = capture_service.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"chat1-measurement-evidence",
        camera=CameraMetadata(width_px=1200, height_px=800),
        media_type="image/png",
        extension=".png",
    )
    capture_service.accept_view(session.session_id, view=CaptureViewType.FRONT)

    capture_package = CanonicalContractBuilder.capture_package(
        project,
        capture_service.get(session.session_id),
    )
    _validator("CapturePackage").validate(capture_package)

    view = capture_package["views"][0]
    assert view["view_type"] == "FRONT"
    assert view["clean_reference_frame"]["artifact_id"] == str(clean.artifact.artifact_id)
    assert view["measurement_frames"][0]["frame_id"] == str(evidence.frame_id)

    ids = SequentialIds()
    measurement_service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    measurement_session = measurement_service.create_session(capture_package["project_id"])

    reference_frame_id = view["clean_reference_frame"]["artifact_id"]
    evidence_frame_id = view["measurement_frames"][0]["frame_id"]
    view_id = view["view_id"]

    anchor_a = measurement_service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=100,
        y_px=200,
    )
    anchor_b = measurement_service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=902,
        y_px=200,
    )
    candidate = measurement_service.add_manual_candidate(
        session_id=measurement_session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="80.20",
        view_id=view_id,
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id=evidence_frame_id,
        uncertainty_mm="0.02",
        instrument_type="DIGITAL_CALIPER",
    )
    measurement_service.confirm_manual_measurement(
        session_id=measurement_session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    measurement_package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=measurement_service.get_session(measurement_session.session_id),
        capture_package=capture_package,
    )
    _validator("MeasurementPackage").validate(measurement_package)

    produced = measurement_package["measurements"][0]
    assert measurement_package["capture_package_id"] == capture_package["capture_package_id"]
    assert produced["view_id"] == view_id
    assert produced["evidence_frame_id"] == evidence_frame_id
    assert produced["source"] == "MANUAL_MEASURED"
    assert produced["verified"] is True
    assert {anchor["coordinate_space"] for anchor in produced["anchors"]} == {"IMAGE_PX"}
    assert {anchor["reference_frame_id"] for anchor in produced["anchors"]} == {
        reference_frame_id
    }

    # The downstream evidence references must resolve to artifacts/frames actually
    # produced by Chat 1, rather than locally invented IDs in Chat 2.
    chat1_measurement_frame_ids = {
        item["frame_id"] for item in view["measurement_frames"]
    }
    assert produced["evidence_frame_id"] in chat1_measurement_frame_ids
    assert produced["anchors"][0]["reference_frame_id"] == view["clean_reference_frame"]["artifact_id"]
