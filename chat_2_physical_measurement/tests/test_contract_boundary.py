import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

CHAT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CHAT_ROOT.parent
sys.path.insert(0, str(CHAT_ROOT / "src"))

from physical_measurement import (  # noqa: E402
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
        return f"{prefix}-CHAT2-{self._value:03d}"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(def_name: str) -> Draft202012Validator:
    schema = load_json(REPO_ROOT / "core" / "contracts" / "mrea_contracts_v1.schema.json")
    scoped = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{def_name}",
    }
    return Draft202012Validator(scoped, format_checker=FormatChecker())


def test_canonical_capture_to_schema_valid_measurement_package() -> None:
    capture = load_json(
        REPO_ROOT / "tests" / "fixtures" / "contracts" / "capture_package_v1.json"
    )
    validator_for("CapturePackage").validate(capture)

    ids = SequentialIds()
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    session = service.create_session(capture["project_id"])
    view = capture["views"][0]
    reference_frame_id = view["clean_reference_frame"]["artifact_id"]

    anchor_a = service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id=reference_frame_id,
        x_px=100,
        y_px=200,
    )
    anchor_b = service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id=reference_frame_id,
        x_px=900,
        y_px=200,
    )
    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="80.20",
        view_id=view["view_id"],
        anchor_a=anchor_a,
        anchor_b=anchor_b,
        uncertainty_mm="0.02",
        instrument_type="DIGITAL_CALIPER",
    )
    confirmed = service.confirm_manual_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=capture,
    )
    validator_for("MeasurementPackage").validate(package)

    assert package["project_id"] == capture["project_id"]
    assert package["part_id"] == capture["part_id"]
    assert package["capture_package_id"] == capture["capture_package_id"]
    assert len(package["measurements"]) == 1

    wire = package["measurements"][0]
    assert wire["measurement_id"] == confirmed.measurement_id
    assert wire["value"] == 80.2
    assert wire["source"] == "MANUAL_MEASURED"
    assert wire["verified"] is True
    assert wire["confirmation_source"] == "USER_CONFIRMED"
    assert {item["coordinate_space"] for item in wire["anchors"]} == {"IMAGE_PX"}
    assert {item["reference_frame_id"] for item in wire["anchors"]} == {
        reference_frame_id
    }


def test_adapter_rejects_session_from_other_project() -> None:
    capture = load_json(
        REPO_ROOT / "tests" / "fixtures" / "contracts" / "capture_package_v1.json"
    )
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=SequentialIds(),
    )
    session = service.create_session("P-OTHER")

    with pytest.raises(ValueError, match="project_id does not match"):
        CanonicalMeasurementAdapter(id_factory=SequentialIds()).build_measurement_package(
            session=session,
            capture_package=capture,
        )


def test_adapter_rejects_unknown_reference_frame() -> None:
    capture = load_json(
        REPO_ROOT / "tests" / "fixtures" / "contracts" / "capture_package_v1.json"
    )
    ids = SequentialIds()
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
    )
    session = service.create_session(capture["project_id"])
    view = capture["views"][0]

    anchor_a = service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id="WRONG-REF",
        x_px=0,
        y_px=0,
    )
    anchor_b = service.create_manual_anchor(
        view_id=view["view_id"],
        reference_frame_id="WRONG-REF",
        x_px=10,
        y_px=0,
    )
    service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="10",
        view_id=view["view_id"],
        anchor_a=anchor_a,
        anchor_b=anchor_b,
    )

    with pytest.raises(ValueError, match="clean reference frame"):
        CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
            session=service.get_session(session.session_id),
            capture_package=capture,
        )
