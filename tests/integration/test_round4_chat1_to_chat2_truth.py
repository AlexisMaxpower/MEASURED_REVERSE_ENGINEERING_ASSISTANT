from __future__ import annotations

from pathlib import Path

import pytest

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


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-R4-X12-{self._value:03d}"


def _add_verified_linear_measurement(
    service: MeasurementSessionService,
    *,
    session_id: str,
    view_id: str,
    reference_frame_id: str,
    evidence_frame_id: str,
    value: str,
):
    anchor_a = service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id=view_id,
        reference_frame_id=reference_frame_id,
        x_px=900,
        y_px=200,
    )
    candidate = service.add_manual_candidate(
        session_id=session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value=value,
        view_id=view_id,
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        evidence_frame_id=evidence_frame_id,
        uncertainty="0.02",
        instrument_type="DIGITAL_CALIPER",
    )
    return service.confirm_measurement(
        session_id=session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )


def test_round4_recapture_lineage_rejects_superseded_measurement_context_without_mutating_truth(
    tmp_path: Path,
) -> None:
    project = Project(
        name="Round 4 recapture boundary",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    capture_repo = JsonCaptureSessionRepository(tmp_path / "capture")
    artifact_store = FileSystemArtifactStore(tmp_path / "artifacts")
    capture = CaptureSessionService(capture_repo, artifact_store)
    capture_session = capture.start(plan)

    clean_v1 = capture.capture_clean_reference(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-clean-v1",
        camera=CameraMetadata(width_px=1200, height_px=800),
    )
    evidence_v1 = capture.capture_measurement_frame(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-evidence-v1",
        camera=CameraMetadata(width_px=1200, height_px=800),
    )
    package_v1 = CanonicalContractBuilder.capture_package(
        project,
        capture.get(capture_session.session_id),
    )
    view_v1 = package_v1["views"][0]

    ids = SequentialIds()
    measurements = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    measurement_session_v1 = measurements.create_session(package_v1["project_id"])
    verified_v1 = _add_verified_linear_measurement(
        measurements,
        session_id=measurement_session_v1.session_id,
        view_id=view_v1["view_id"],
        reference_frame_id=view_v1["clean_reference_frame"]["artifact_id"],
        evidence_frame_id=view_v1["measurement_frames"][0]["frame_id"],
        value="80.20",
    )
    package_measurement_v1 = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=measurements.get_session(measurement_session_v1.session_id),
        capture_package=package_v1,
    )
    assert package_measurement_v1["measurements"][0]["verified"] is True

    clean_v2 = capture.recapture_clean_reference(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-clean-v2",
        camera=CameraMetadata(width_px=1200, height_px=800),
    )
    evidence_v2 = capture.capture_measurement_frame(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-evidence-v2",
        camera=CameraMetadata(width_px=1200, height_px=800),
    )
    package_v2 = CanonicalContractBuilder.capture_package(
        project,
        capture.get(capture_session.session_id),
    )
    view_v2 = package_v2["views"][0]

    assert clean_v2.supersedes_frame_id == clean_v1.frame_id
    assert evidence_v1.source_clean_reference_frame_id == clean_v1.frame_id
    assert evidence_v2.source_clean_reference_frame_id == clean_v2.frame_id
    assert view_v2["clean_reference_frame"]["artifact_id"] == str(clean_v2.artifact.artifact_id)
    assert [item["frame_id"] for item in view_v2["measurement_frames"]] == [
        str(evidence_v2.frame_id)
    ]

    with pytest.raises(ValueError, match="reference_frame_id does not match"):
        CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
            session=measurements.get_session(measurement_session_v1.session_id),
            capture_package=package_v2,
        )

    still_verified = measurements.get_session(measurement_session_v1.session_id).measurements[0]
    assert still_verified.measurement_id == verified_v1.measurement_id
    assert still_verified.is_verified is True
    assert float(still_verified.value) == pytest.approx(80.2)

    measurement_session_v2 = measurements.create_session(package_v2["project_id"])
    verified_v2 = _add_verified_linear_measurement(
        measurements,
        session_id=measurement_session_v2.session_id,
        view_id=view_v2["view_id"],
        reference_frame_id=view_v2["clean_reference_frame"]["artifact_id"],
        evidence_frame_id=view_v2["measurement_frames"][0]["frame_id"],
        value="80.20",
    )
    package_measurement_v2 = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=measurements.get_session(measurement_session_v2.session_id),
        capture_package=package_v2,
    )
    wire = package_measurement_v2["measurements"][0]

    assert verified_v2.is_verified is True
    assert wire["verified"] is True
    assert {anchor["reference_frame_id"] for anchor in wire["anchors"]} == {
        view_v2["clean_reference_frame"]["artifact_id"]
    }
    assert wire["evidence_frame_id"] == str(evidence_v2.frame_id)
