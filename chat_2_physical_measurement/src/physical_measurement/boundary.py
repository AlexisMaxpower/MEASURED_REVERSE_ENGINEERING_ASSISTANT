from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .models import FeatureAnchor, MeasurementSession, PhysicalMeasurement


CAPTURE_SCHEMA_VERSION = "mrea.capture-package.v1"
MEASUREMENT_SCHEMA_VERSION = "mrea.measurement-package.v1"


def _as_number(value: Decimal | int | float) -> int | float:
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def _utc_rfc3339(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("canonical timestamps must be timezone-aware")
    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")


class CanonicalMeasurementAdapter:
    """Maps Chat 2 internal physical-measurement models to canonical wire contracts."""

    def __init__(self, *, id_factory: Callable[[str], str] | None = None) -> None:
        self._id_factory = id_factory or (lambda prefix: f"{prefix}_{uuid4().hex}")

    def build_measurement_package(
        self,
        *,
        session: MeasurementSession,
        capture_package: Mapping[str, Any],
    ) -> dict[str, Any]:
        context = self._capture_context(capture_package)

        if session.project_id != context["project_id"]:
            raise ValueError(
                "measurement session project_id does not match CapturePackage project_id"
            )

        measurements = [
            self._serialize_measurement(measurement, context["views"])
            for measurement in session.measurements
        ]

        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "measurement_package_id": self._id_factory("MP"),
            "project_id": context["project_id"],
            "part_id": context["part_id"],
            "capture_package_id": context["capture_package_id"],
            "measurements": measurements,
        }

    def _capture_context(self, capture_package: Mapping[str, Any]) -> dict[str, Any]:
        if capture_package.get("schema_version") != CAPTURE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported CapturePackage schema_version: "
                f"{capture_package.get('schema_version')!r}"
            )

        required_ids = ("capture_package_id", "project_id", "part_id")
        values: dict[str, str] = {}
        for field_name in required_ids:
            value = capture_package.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"CapturePackage {field_name} must be a non-empty string")
            values[field_name] = value

        raw_views = capture_package.get("views")
        if not isinstance(raw_views, list) or not raw_views:
            raise ValueError("CapturePackage must contain at least one view")

        views: dict[str, dict[str, Any]] = {}
        for view in raw_views:
            if not isinstance(view, Mapping):
                raise ValueError("CapturePackage view must be an object")
            view_id = view.get("view_id")
            clean_reference = view.get("clean_reference_frame")
            if not isinstance(view_id, str) or not view_id:
                raise ValueError("CapturePackage view_id must be a non-empty string")
            if not isinstance(clean_reference, Mapping):
                raise ValueError(f"view {view_id} is missing clean_reference_frame")
            reference_frame_id = clean_reference.get("artifact_id")
            if not isinstance(reference_frame_id, str) or not reference_frame_id:
                raise ValueError(
                    f"view {view_id} clean_reference_frame artifact_id is required"
                )

            measurement_frames = view.get("measurement_frames", [])
            if not isinstance(measurement_frames, list):
                raise ValueError(f"view {view_id} measurement_frames must be an array")

            evidence_frame_ids: set[str] = set()
            for frame in measurement_frames:
                if isinstance(frame, Mapping):
                    frame_id = frame.get("frame_id")
                    if isinstance(frame_id, str) and frame_id:
                        evidence_frame_ids.add(frame_id)

            views[view_id] = {
                "reference_frame_id": reference_frame_id,
                "evidence_frame_ids": evidence_frame_ids,
            }

        return {**values, "views": views}

    def _serialize_measurement(
        self,
        measurement: PhysicalMeasurement,
        views: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        view = views.get(measurement.view_id)
        if view is None:
            raise ValueError(
                f"measurement {measurement.measurement_id} references unknown view_id "
                f"{measurement.view_id!r}"
            )

        expected_reference_frame_id = view["reference_frame_id"]
        for anchor in (measurement.anchor_a, measurement.anchor_b):
            if anchor.reference_frame_id != expected_reference_frame_id:
                raise ValueError(
                    f"anchor {anchor.anchor_id} reference_frame_id does not match "
                    f"CapturePackage clean reference frame"
                )

        if measurement.evidence_frame_id is not None:
            evidence_frame_ids = view["evidence_frame_ids"]
            if measurement.evidence_frame_id not in evidence_frame_ids:
                raise ValueError(
                    f"measurement {measurement.measurement_id} evidence_frame_id "
                    f"is not present in CapturePackage view"
                )

        return {
            "measurement_id": measurement.measurement_id,
            "type": measurement.measurement_type.value,
            "value": _as_number(measurement.value),
            "unit": measurement.unit,
            "uncertainty": (
                _as_number(measurement.uncertainty)
                if measurement.uncertainty is not None
                else None
            ),
            "source": measurement.source.value,
            "view_id": measurement.view_id,
            "anchors": [
                self._serialize_anchor(measurement.anchor_a),
                self._serialize_anchor(measurement.anchor_b),
            ],
            "evidence_frame_id": measurement.evidence_frame_id,
            "instrument": (
                {"type": measurement.instrument_type}
                if measurement.instrument_type is not None
                else None
            ),
            "confidence": None,
            "verified": measurement.is_verified,
            "confirmation_source": (
                measurement.confirmation_source.value
                if measurement.confirmation_source is not None
                else None
            ),
            "created_at": _utc_rfc3339(measurement.created_at),
        }

    @staticmethod
    def _serialize_anchor(anchor: FeatureAnchor) -> dict[str, Any]:
        return {
            "anchor_id": anchor.anchor_id,
            "view_id": anchor.view_id,
            "reference_frame_id": anchor.reference_frame_id,
            "coordinate_space": "IMAGE_PX",
            "x": float(anchor.x_px),
            "y": float(anchor.y_px),
            "feature_id": None,
        }
