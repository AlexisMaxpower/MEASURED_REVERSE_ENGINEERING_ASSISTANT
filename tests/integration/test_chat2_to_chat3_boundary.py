from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from physical_measurement import CanonicalMeasurementAdapter, InMemoryMeasurementSessionRepository, MeasurementSessionService, MeasurementType
from mrea_geometry import CanonicalInputAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contracts"


class SequentialIds:
    def __init__(self) -> None:
        self._value = 0

    def __call__(self, prefix: str) -> str:
        self._value += 1
        return f"{prefix}-XSLICE-{self._value:03d}"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_real_chat2_image_px_output_is_normalized_by_chat3_using_capture_homography() -> None:
    capture = copy.deepcopy(_load("capture_package_v1.json"))
    view = capture["views"][0]
    view["calibration"]["homography"] = [0.1, 0.0, 5.0, 0.0, 0.2, 7.0, 0.0, 0.0, 1.0]

    ids = SequentialIds()
    service = MeasurementSessionService(InMemoryMeasurementSessionRepository(), id_factory=ids)
    session = service.create_session(capture["project_id"])
    reference_frame_id = view["clean_reference_frame"]["artifact_id"]
    anchor_a = service.create_manual_anchor(view_id=view["view_id"], reference_frame_id=reference_frame_id, x_px=100, y_px=200)
    anchor_b = service.create_manual_anchor(view_id=view["view_id"], reference_frame_id=reference_frame_id, x_px=900, y_px=200)
    candidate = service.add_manual_candidate(session_id=session.session_id, measurement_type=MeasurementType.LINEAR_EXTERNAL, value="80.20", view_id=view["view_id"], anchor_a=anchor_a, anchor_b=anchor_b, uncertainty_mm="0.02", instrument_type="DIGITAL_CALIPER")
    service.confirm_manual_measurement(session_id=session.session_id, measurement_id=candidate.measurement_id, explicit_user_confirmation=True)
    measurement_package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(session=service.get_session(session.session_id), capture_package=capture)

    assert {a["coordinate_space"] for a in measurement_package["measurements"][0]["anchors"]} == {"IMAGE_PX"}
    normalized = CanonicalInputAdapter().from_packages(capture, measurement_package)
    measurement = normalized.measurements[0]
    assert normalized.coordinate_system == "MAT_XY_MM"
    assert measurement.measurement_id == candidate.measurement_id
    assert measurement.value == pytest.approx(80.2)
    assert measurement.verified is True
    assert measurement.source == "MANUAL_MEASURED"
    assert measurement.anchors[0].point.x == pytest.approx(15.0)
    assert measurement.anchors[0].point.y == pytest.approx(47.0)
    assert measurement.anchors[1].point.x == pytest.approx(95.0)
    assert measurement.anchors[1].point.y == pytest.approx(47.0)
