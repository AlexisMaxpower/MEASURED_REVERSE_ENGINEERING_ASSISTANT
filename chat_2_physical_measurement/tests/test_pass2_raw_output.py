from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

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


class PrefixSequentialIds:
    """Deterministic per-prefix IDs shared by service and boundary adapter."""

    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._values[prefix] += 1
        return f"{prefix}-CHAT2-P2-{self._values[prefix]:03d}"


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


def build_actual_raw_package() -> tuple[dict, dict]:
    capture = load_json(CHAT_ROOT / "tests" / "fixtures" / "capture_package_raw_image_px_v1.json")
    fixed_time = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    ids = PrefixSequentialIds()
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=ids,
        clock=lambda: fixed_time,
    )
    session = service.create_session(capture["project_id"])
    view = capture["views"][0]
    view_id = view["view_id"]
    reference_frame_id = view["clean_reference_frame"]["artifact_id"]
    evidence_frame_id = view["measurement_frames"][0]["frame_id"]

    def add_verified(
        *,
        measurement_type: MeasurementType,
        value: str,
        anchor_a_xy: tuple[float, float],
        anchor_b_xy: tuple[float, float],
    ) -> None:
        anchor_a = service.create_manual_anchor(
            view_id=view_id,
            reference_frame_id=reference_frame_id,
            x_px=anchor_a_xy[0],
            y_px=anchor_a_xy[1],
        )
        anchor_b = service.create_manual_anchor(
            view_id=view_id,
            reference_frame_id=reference_frame_id,
            x_px=anchor_b_xy[0],
            y_px=anchor_b_xy[1],
        )
        candidate = service.add_manual_candidate(
            session_id=session.session_id,
            measurement_type=measurement_type,
            value=value,
            view_id=view_id,
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            evidence_frame_id=evidence_frame_id,
            uncertainty_mm="0.02",
            instrument_type="DIGITAL_CALIPER",
        )
        service.confirm_manual_measurement(
            session_id=session.session_id,
            measurement_id=candidate.measurement_id,
            explicit_user_confirmation=True,
        )

    # With the upstream 0.1 mm/px calibration these raw anchors are also useful
    # to Chat 3: 802 px -> 80.2 mm and 51 px -> 5.1 mm after normalization.
    add_verified(
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="80.20",
        anchor_a_xy=(100, 200),
        anchor_b_xy=(902, 200),
    )
    add_verified(
        measurement_type=MeasurementType.DIAMETER_INTERNAL,
        value="5.10",
        anchor_a_xy=(500, 300),
        anchor_b_xy=(551, 300),
    )

    package = CanonicalMeasurementAdapter(id_factory=ids).build_measurement_package(
        session=service.get_session(session.session_id),
        capture_package=capture,
    )
    return capture, package


def test_pass2_actual_raw_package_matches_committed_specimen_and_schema() -> None:
    capture, package = build_actual_raw_package()
    expected = load_json(CHAT_ROOT / "tests" / "fixtures" / "measurement_package_raw_image_px_v1.json")

    validator_for("CapturePackage").validate(capture)
    validator_for("MeasurementPackage").validate(package)
    assert package == expected


def test_pass2_specimen_preserves_raw_measurement_semantics() -> None:
    capture, package = build_actual_raw_package()

    assert len(package["measurements"]) == 2
    assert [item["type"] for item in package["measurements"]] == [
        "LINEAR_EXTERNAL",
        "DIAMETER_INTERNAL",
    ]
    assert all(item["verified"] is True for item in package["measurements"])
    assert all(item["source"] == "MANUAL_MEASURED" for item in package["measurements"])
    assert all(
        item["confirmation_source"] == "USER_CONFIRMED"
        for item in package["measurements"]
    )
    assert all(
        item["evidence_frame_id"] == "FRAME-FRONT-MEAS-001"
        for item in package["measurements"]
    )

    anchors = [anchor for item in package["measurements"] for anchor in item["anchors"]]
    assert all(anchor["coordinate_space"] == "IMAGE_PX" for anchor in anchors)
    assert all(anchor["feature_id"] is None for anchor in anchors)
    assert all(
        anchor["reference_frame_id"] == "A-FRONT-CLEAN-RAW-001"
        for anchor in anchors
    )

    # Calibration is intentionally upstream context only; Chat 2 leaves anchors raw.
    assert capture["views"][0]["calibration"]["coordinate_system"] == "MAT_XY_MM"
    assert capture["views"][0]["calibration"]["homography"] == [
        0.1, 0, 0, 0, 0.1, 0, 0, 0, 1
    ]


def test_injected_clock_makes_timestamps_deterministic() -> None:
    fixed = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: fixed,
    )
    session = service.create_session("P-CLOCK")
    a = service.create_manual_anchor(
        view_id="VIEW-CLOCK", reference_frame_id="REF-CLOCK", x_px=0, y_px=0
    )
    b = service.create_manual_anchor(
        view_id="VIEW-CLOCK", reference_frame_id="REF-CLOCK", x_px=5, y_px=0
    )
    candidate = service.add_manual_candidate(
        session_id=session.session_id,
        measurement_type=MeasurementType.LINEAR_EXTERNAL,
        value="5",
        view_id="VIEW-CLOCK",
        anchor_a=a,
        anchor_b=b,
    )
    confirmed = service.confirm_manual_measurement(
        session_id=session.session_id,
        measurement_id=candidate.measurement_id,
        explicit_user_confirmation=True,
    )

    assert session.created_at == fixed
    assert candidate.created_at == fixed
    assert confirmed.confirmed_at == fixed


def test_injected_clock_must_be_timezone_aware() -> None:
    import pytest

    service = MeasurementSessionService(
        InMemoryMeasurementSessionRepository(),
        id_factory=PrefixSequentialIds(),
        clock=lambda: datetime(2026, 9, 29, 12, 0, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        service.create_session("P-CLOCK")
