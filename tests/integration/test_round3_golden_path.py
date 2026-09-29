from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
from jsonschema import Draft202012Validator, FormatChecker

from mrea_capture import (
    CalibrationService,
    CameraMetadata,
    CanonicalContractBuilder,
    CapturePlanService,
    CaptureSessionService,
    CaptureViewType,
    FileSystemArtifactStore,
    JsonCaptureSessionRepository,
    MeasurementMatProfile,
    OpenCvCharucoCalibrationDetector,
    PartContext,
    Project,
)
from physical_measurement import (
    CanonicalMeasurementAdapter,
    HandsFreeMeasurementController,
    InMemoryMeasurementSessionRepository,
    MeasurementCandidateContext,
    MeasurementSessionService,
    MeasurementType,
)
from mrea_geometry import (
    CanonicalInputAdapter,
    GeometryPipeline,
    Line,
    Point2D,
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
    RevisionOrigin,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "core" / "contracts" / "mrea_contracts_v1.schema.json"
NOW = datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc)


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-ROUND3-GOLDEN-{self._value:03d}"


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


def _mat_to_image(homography: list[float], x_mm: float, y_mm: float) -> tuple[float, float]:
    image_to_mat = np.asarray(homography, dtype=float).reshape(3, 3)
    mat_to_image = np.linalg.inv(image_to_mat)
    point = mat_to_image @ np.asarray([x_mm, y_mm, 1.0], dtype=float)
    assert abs(point[2]) > 1e-12
    return float(point[0] / point[2]), float(point[1] / point[2])


def test_round3_capture_to_physical_instance_golden_path(tmp_path: Path) -> None:
    # Chat 1: create real immutable capture evidence and deterministic calibration.
    profile = MeasurementMatProfile(
        mat_id="MAT-ROUND3-GOLDEN",
        squares_x=5,
        squares_y=7,
        square_length_mm=20.0,
        marker_length_mm=14.0,
    )
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard((5, 7), 20.0, 14.0, dictionary)
    image = board.generateImage((1000, 1400), marginSize=50)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    project = Project(
        name="Round 3 golden plate",
        part=PartContext(part_type="flat plate"),
    )
    plan = CapturePlanService().create_plan(project, views=[CaptureViewType.FRONT])
    capture_repository = JsonCaptureSessionRepository(tmp_path / "capture")
    artifact_store = FileSystemArtifactStore(tmp_path / "artifacts")
    capture_service = CaptureSessionService(capture_repository, artifact_store)
    capture_session = capture_service.start(plan)

    clean = capture_service.capture_clean_reference(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=encoded.tobytes(),
        camera=CameraMetadata(width_px=1000, height_px=1400),
        captured_at=NOW,
        media_type="image/png",
        extension=".png",
    )
    evidence = capture_service.capture_measurement_frame(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=encoded.tobytes(),
        camera=CameraMetadata(width_px=1000, height_px=1400),
        captured_at=NOW + timedelta(seconds=1),
        media_type="image/png",
        extension=".png",
    )
    calibration = CalibrationService(
        capture_repository,
        artifact_store,
        OpenCvCharucoCalibrationDetector(),
    ).calibrate_view(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        profile=profile,
    )
    capture_service.accept_view(
        capture_session.session_id,
        view=CaptureViewType.FRONT,
        accepted_at=NOW + timedelta(seconds=2),
    )
    capture_package = CanonicalContractBuilder.capture_package(
        project,
        capture_service.get(capture_session.session_id),
    )
    _validator("CapturePackage").validate(capture_package)
    assert calibration.detected_charuco_corner_count == 24

    view = capture_package["views"][0]
    assert view["clean_reference_frame"]["artifact_id"] == str(clean.artifact.artifact_id)
    assert view["measurement_frames"][0]["frame_id"] == str(evidence.frame_id)
    assert view["calibration"]["coordinate_system"] == "MAT_XY_MM"

    # Chat 2: create a voice-reported physical value from IMAGE_PX anchors and
    # require explicit user confirmation before it can become verified truth.
    anchor_a_px = _mat_to_image(view["calibration"]["homography"], 20.0, 40.0)
    anchor_b_px = _mat_to_image(view["calibration"]["homography"], 80.0, 40.0)

    ids = SequentialIds()
    measurement_service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
        clock=lambda: NOW + timedelta(seconds=3),
    )
    measurement_session = measurement_service.create_session(capture_package["project_id"])
    reference_frame_id = view["clean_reference_frame"]["artifact_id"]
    evidence_frame_id = view["measurement_frames"][0]["frame_id"]

    anchor_a = measurement_service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id=reference_frame_id,
        x_px=anchor_a_px[0],
        y_px=anchor_a_px[1],
    )
    anchor_b = measurement_service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id=reference_frame_id,
        x_px=anchor_b_px[0],
        y_px=anchor_b_px[1],
    )
    controller = HandsFreeMeasurementController(
        service=measurement_service,
        session_id=measurement_session.session_id,
        context=MeasurementCandidateContext(
            measurement_type=MeasurementType.LINEAR_EXTERNAL,
            view_id=view["view_id"],
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            uncertainty_mm="0.02",
            instrument_type="DIGITAL_CALIPER",
        ),
    )

    candidate = controller.process_voice_command("замер 60,0").measurement
    assert candidate is not None
    assert candidate.is_verified is False
    verified = controller.process_voice_command("подтвердить").measurement
    assert verified is not None
    assert verified.is_verified is True

    measurement_package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=measurement_service.get_session(measurement_session.session_id),
        capture_package=capture_package,
    )
    _validator("MeasurementPackage").validate(measurement_package)
    wire_measurement = measurement_package["measurements"][0]
    assert wire_measurement["source"] == "VOICE_REPORTED"
    assert wire_measurement["confirmation_source"] == "USER_CONFIRMED"
    assert wire_measurement["verified"] is True
    assert {item["coordinate_space"] for item in wire_measurement["anchors"]} == {"IMAGE_PX"}

    # Chat 3: normalize the raw pixel anchors back to MAT_XY_MM and bind the
    # verified measurement to truthful vision-derived geometry without changing it.
    context = CanonicalInputAdapter().from_packages(capture_package, measurement_package)
    primitives = (
        Line(
            entity_id="L-BOTTOM",
            start=Point2D(20.0, 20.0),
            end=Point2D(80.0, 20.0),
            source="VISION_DETECTED",
            confidence=0.99,
        ),
        Line(
            entity_id="L-RIGHT",
            start=Point2D(80.0, 20.0),
            end=Point2D(80.0, 60.0),
            source="VISION_DETECTED",
            confidence=0.99,
        ),
        Line(
            entity_id="L-TOP",
            start=Point2D(80.0, 60.0),
            end=Point2D(20.0, 60.0),
            source="VISION_DETECTED",
            confidence=0.99,
        ),
        Line(
            entity_id="L-LEFT",
            start=Point2D(20.0, 60.0),
            end=Point2D(20.0, 20.0),
            source="VISION_DETECTED",
            confidence=0.99,
        ),
    )
    draft = GeometryPipeline().build(primitives, context.measurements)
    assert context.coordinate_system == "MAT_XY_MM"
    assert draft.unresolved == ()
    assert draft.conflicts == ()
    assert len(draft.dimensions) == 1
    assert draft.dimensions[0].measurement_id == verified.measurement_id
    assert draft.dimensions[0].value == 60.0

    sketch_package = SketchPackageBuilder().build(
        draft,
        context,
        sketch_package_id="SP-ROUND3-GOLDEN",
    )
    _validator("SketchPackage").validate(sketch_package)
    assert sketch_package["unresolved"] == []
    assert sketch_package["dimensions"][0]["verified"] is True
    assert sketch_package["dimensions"][0]["provenance"] == "VOICE_REPORTED"

    # Chat 4: generic CAD transfer/read-back must verify the exact canonical value.
    transfer = execute_cad_transfer_v1(
        sketch_package=sketch_package,
        adapter=TestDoubleCadAdapter(),
        cad_package_id="CAD-ROUND3-GOLDEN",
        report_id="CADV-ROUND3-GOLDEN",
    )
    _validator("CADPackage").validate(transfer.cad_package)
    _validator("CADVerificationReport").validate(transfer.cad_verification_report)
    assert transfer.cad_verification_report["overall_status"] == "VERIFIED"
    assert [item["measurement_id"] for item in transfer.cad_verification_report["items"]] == [
        verified.measurement_id
    ]

    # Chat 5: only verified CAD can become a manufacturing record, and that
    # manufacturing record is the sole entry point for a concrete physical item.
    lifecycle_store = InMemoryLifecycleStore()
    revision = CADRevisionPreparationService(lifecycle_store).prepare(
        revision_id="REV-ROUND3-GOLDEN",
        part_id=capture_package["part_id"],
        revision_code="REV03",
        created_at=NOW + timedelta(minutes=1),
        cad_package=transfer.cad_package,
        verification_report=transfer.cad_verification_report,
        event_id="EV-ROUND3-REVISION",
    )
    assert revision.origin is RevisionOrigin.CAD_TRANSFER

    manufacturing = ManufacturingService(lifecycle_store)
    assert manufacturing.is_revision_eligible(revision.revision_id) is True
    manufacturing.record(
        ManufacturingRecord(
            manufacturing_id="MFG-ROUND3-GOLDEN",
            revision_id=revision.revision_id,
            material="PETG",
            method="FDM",
            manufactured_at=NOW + timedelta(minutes=2),
            machine="GOLDEN-PRINTER",
        ),
        event_id="EV-ROUND3-MANUFACTURED",
    )

    physical = PhysicalPartLifecycleService(lifecycle_store)
    instance = physical.register_manufactured(
        instance_id="PI-ROUND3-GOLDEN",
        manufacturing_id="MFG-ROUND3-GOLDEN",
        physical_event_id="PH-ROUND3-MANUFACTURED",
    )
    assert instance.part_id == capture_package["part_id"]
    assert instance.revision_id == revision.revision_id
    assert instance.manufacturing_id == "MFG-ROUND3-GOLDEN"
    assert (
        PhysicalPartStateProjection(lifecycle_store).for_instance(instance.instance_id)
        is PhysicalPartState.MANUFACTURED
    )
