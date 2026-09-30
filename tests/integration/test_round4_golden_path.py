from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mrea_capture import (
    CalibrationResult,
    CalibrationService,
    CameraMetadata,
    CanonicalContractBuilder,
    CapturePlanService,
    CaptureSessionService,
    CaptureViewType,
    FileSystemArtifactStore,
    JsonCaptureSessionRepository,
    MeasurementMatProfile,
    PartContext,
    Project,
)
from physical_measurement import (
    CanonicalMeasurementAdapter,
    InMemoryMeasurementSessionRepository,
    MeasurementSessionService,
    MeasurementType,
)
from mrea_geometry import (
    CanonicalInputAdapter,
    ConstraintResolver,
    GeometryPipeline,
    Line,
    Point2D,
    PointEntity,
    SketchPackageBuilder,
)
from mrea_cad_bridge import TestDoubleCadAdapter, execute_cad_transfer_v1
from mrea_lifecycle import (
    CADRevisionPreparationService,
    InMemoryLifecycleStore,
    ManufacturingRecord,
    ManufacturingService,
    PhysicalPartLifecycleService,
    PhysicalPartState,
    PhysicalPartStateProjection,
)


NOW = datetime(2026, 9, 30, 17, 0, tzinfo=timezone.utc)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-R4-GOLDEN-{self._value:03d}"


class IdentityDetector:
    def detect(self, image_bytes, *, profile, view, source_frame_id):
        return CalibrationResult(
            view=view,
            source_frame_id=source_frame_id,
            mat_id=profile.mat_id,
            homography=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            detected_marker_count=12,
            detected_charuco_corner_count=24,
            reprojection_rmse_mm=0.1,
        )


def test_round4_truth_hardening_golden_path(tmp_path: Path) -> None:
    # Chat 1: immutable recapture lineage and active-attempt evidence.
    project = Project(
        name="Round 4 truth-hardening golden path",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    repo = JsonCaptureSessionRepository(tmp_path / "capture")
    store = FileSystemArtifactStore(tmp_path / "artifacts")
    capture = CaptureSessionService(repo, store)
    session = capture.start(plan)

    clean_v1 = capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-golden-clean-v1",
        camera=CameraMetadata(width_px=1000, height_px=800),
        captured_at=NOW,
    )
    evidence_v1 = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-golden-evidence-v1",
        camera=CameraMetadata(width_px=1000, height_px=800),
        captured_at=NOW + timedelta(seconds=1),
    )
    clean_v2 = capture.recapture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-golden-clean-v2",
        camera=CameraMetadata(width_px=1000, height_px=800),
        captured_at=NOW + timedelta(seconds=2),
    )
    evidence_v2 = capture.capture_measurement_frame(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"round4-golden-evidence-v2",
        camera=CameraMetadata(width_px=1000, height_px=800),
        captured_at=NOW + timedelta(seconds=3),
    )
    profile = MeasurementMatProfile(
        mat_id="MAT-R4-GOLDEN",
        squares_x=5,
        squares_y=7,
        square_length_mm=20.0,
        marker_length_mm=14.0,
    )
    CalibrationService(repo, store, IdentityDetector()).calibrate_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        profile=profile,
    )
    capture.accept_view(
        session.session_id,
        view=CaptureViewType.FRONT,
        accepted_at=NOW + timedelta(seconds=4),
    )
    capture_package = CanonicalContractBuilder.capture_package(
        project,
        capture.get(session.session_id),
    )
    view = capture_package["views"][0]
    assert clean_v2.supersedes_frame_id == clean_v1.frame_id
    assert evidence_v1.source_clean_reference_frame_id == clean_v1.frame_id
    assert evidence_v2.source_clean_reference_frame_id == clean_v2.frame_id
    assert view["clean_reference_frame"]["artifact_id"] == str(clean_v2.artifact.artifact_id)
    assert [item["frame_id"] for item in view["measurement_frames"]] == [str(evidence_v2.frame_id)]

    # Chat 2: a verified 3-anchor ANGLE stays raw IMAGE_PX, deg and uncertainty-aware.
    ids = SequentialIds()
    measurement_service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
        clock=lambda: NOW + timedelta(seconds=5),
    )
    measurement_session = measurement_service.create_session(capture_package["project_id"])
    reference_id = view["clean_reference_frame"]["artifact_id"]
    anchors = tuple(
        measurement_service.create_manual_anchor(
            view_id=view["view_id"],
            reference_frame_id=reference_id,
            x_px=x,
            y_px=y,
        )
        for x, y in ((10.0, 40.0), (30.0, 60.0), (50.0, 40.0))
    )
    angle = measurement_service.add_manual_candidate(
        session_id=measurement_session.session_id,
        measurement_type=MeasurementType.ANGLE,
        value="90.0",
        view_id=view["view_id"],
        anchor_a=anchors[0],
        anchor_b=anchors[1],
        anchor_c=anchors[2],
        evidence_frame_id=str(evidence_v2.frame_id),
        uncertainty="0.5",
    )
    measurement_service.confirm_measurement(
        session_id=measurement_session.session_id,
        measurement_id=angle.measurement_id,
        explicit_user_confirmation=True,
    )
    measurement_package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=measurement_service.get_session(measurement_session.session_id),
        capture_package=capture_package,
    )
    wire = measurement_package["measurements"][0]
    assert wire["unit"] == "deg"
    assert wire["uncertainty"] == pytest.approx(0.5)
    assert len(wire["anchors"]) == 3
    assert {item["coordinate_space"] for item in wire["anchors"]} == {"IMAGE_PX"}
    assert {item["reference_frame_id"] for item in wire["anchors"]} == {reference_id}

    # Chat 3: normalize, preserve physical uncertainty, bind and resolve a safe relation.
    context = CanonicalInputAdapter().from_packages(capture_package, measurement_package)
    normalized = context.measurements[0]
    assert normalized.unit == "deg"
    assert len(normalized.anchors) == 3
    assert hasattr(normalized, "uncertainty")
    assert normalized.uncertainty == pytest.approx(0.5)

    primitives = (
        PointEntity("P-R4-A", Point2D(10.0, 40.0), confidence=0.99),
        PointEntity("P-R4-B", Point2D(30.0, 60.0), confidence=0.99),
        PointEntity("P-R4-C", Point2D(50.0, 40.0), confidence=0.99),
        Line(
            "L-R4-SAFE-H",
            Point2D(0.0, 100.0),
            Point2D(20.0, 100.0),
            confidence=0.99,
        ),
    )
    draft = GeometryPipeline().build(primitives, context.measurements)
    assert draft.unresolved == ()
    assert len(draft.dimensions) == 1
    assert hasattr(draft.dimensions[0], "uncertainty")
    assert draft.dimensions[0].uncertainty == pytest.approx(0.5)

    resolution = ConstraintResolver().resolve(draft)
    assert any(item.kind == "HORIZONTAL" and item.entity_ids == ("L-R4-SAFE-H",) for item in resolution.constraints)
    sketch = SketchPackageBuilder().build(
        draft,
        context,
        sketch_package_id="SP-R4-GOLDEN",
        constraint_resolution=resolution,
    )
    assert any(item["type"] == "HORIZONTAL" for item in sketch["constraints"])

    # Chat 4: vendor-neutral transfer verifies the physical ANGLE and preserves relations.
    transfer = execute_cad_transfer_v1(
        sketch_package=sketch,
        adapter=TestDoubleCadAdapter(),
        cad_package_id="CAD-R4-GOLDEN",
        report_id="CADV-R4-GOLDEN",
    )
    assert transfer.cad_verification_report["overall_status"] == "VERIFIED"
    assert transfer.mapped_sketch_package.constraints == tuple(sketch["constraints"])

    # Chat 5 positive generic-software path remains eligible; runtime-gated vendor
    # UNVERIFIED behavior is covered separately by the Round-4 Chat4->Chat5 gate.
    lifecycle = InMemoryLifecycleStore()
    revision = CADRevisionPreparationService(lifecycle).prepare(
        revision_id="REV-R4-GOLDEN",
        part_id=capture_package["part_id"],
        revision_code="REV04",
        created_at=NOW + timedelta(minutes=1),
        cad_package=transfer.cad_package,
        verification_report=transfer.cad_verification_report,
        event_id="EV-R4-GOLDEN-REV",
    )
    manufacturing = ManufacturingService(lifecycle)
    assert manufacturing.is_revision_eligible(revision.revision_id) is True
    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="MFG-R4-GOLDEN",
            revision_id=revision.revision_id,
            material="PETG",
            method="FDM",
            manufactured_at=NOW + timedelta(minutes=2),
        ),
        event_id="EV-R4-GOLDEN-MFG",
    )
    physical = PhysicalPartLifecycleService(lifecycle)
    instance = physical.register_manufactured(
        instance_id="PI-R4-GOLDEN",
        manufacturing_id="MFG-R4-GOLDEN",
        physical_event_id="PH-R4-GOLDEN-MFG",
    )
    assert PhysicalPartStateProjection(lifecycle).for_instance(instance.instance_id) is PhysicalPartState.MANUFACTURED
