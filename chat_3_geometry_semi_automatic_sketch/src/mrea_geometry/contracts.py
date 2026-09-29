from __future__ import annotations

from dataclasses import dataclass

from .models import AnchorRef, MeasurementRef, Point2D


@dataclass(frozen=True, slots=True)
class CanonicalGeometryInput:
    project_id: str
    part_id: str
    capture_package_id: str
    measurement_package_id: str
    view_id: str
    source_view_ids: tuple[str, ...]
    coordinate_system: str
    measurements: tuple[MeasurementRef, ...]


class CanonicalInputAdapter:
    """Adapter from Integrator-owned v1 dictionaries into Chat 3 internal models."""

    def from_packages(
        self,
        capture_package: dict,
        measurement_package: dict,
        *,
        view_type: str = "FRONT",
    ) -> CanonicalGeometryInput:
        if capture_package.get("schema_version") != "mrea.capture-package.v1":
            raise ValueError("unsupported CapturePackage version")
        if measurement_package.get("schema_version") != "mrea.measurement-package.v1":
            raise ValueError("unsupported MeasurementPackage version")

        for key in ("project_id", "part_id"):
            if capture_package.get(key) != measurement_package.get(key):
                raise ValueError(f"CapturePackage/MeasurementPackage {key} mismatch")
        if measurement_package.get("capture_package_id") != capture_package.get("capture_package_id"):
            raise ValueError("MeasurementPackage points to a different CapturePackage")

        views = [view for view in capture_package.get("views", []) if view.get("view_type") == view_type]
        if len(views) != 1:
            raise ValueError(f"expected exactly one {view_type} view")
        view = views[0]
        view_id = view["view_id"]
        calibration = view.get("calibration") or {}
        if calibration.get("coordinate_system") != "MAT_XY_MM":
            raise ValueError("v1 geometry baseline requires MAT_XY_MM calibration")

        normalized: list[MeasurementRef] = []
        for item in measurement_package.get("measurements", []):
            if item.get("view_id") != view_id:
                continue
            anchors: list[AnchorRef] = []
            for anchor in item.get("anchors", []):
                if anchor.get("view_id") != view_id:
                    raise ValueError("measurement anchor belongs to a different view")
                if anchor.get("coordinate_space") != "MAT_XY_MM":
                    raise ValueError("v1 FRONT baseline requires MAT_XY_MM anchors")
                anchors.append(
                    AnchorRef(
                        anchor_id=anchor["anchor_id"],
                        point=Point2D(float(anchor["x"]), float(anchor["y"])),
                        feature_id=anchor.get("feature_id"),
                    )
                )
            normalized.append(
                MeasurementRef(
                    measurement_id=item["measurement_id"],
                    measurement_type=item["type"],
                    value=float(item["value"]),
                    unit=item["unit"],
                    verified=bool(item["verified"]),
                    source=item["source"],
                    anchors=tuple(anchors),
                )
            )

        return CanonicalGeometryInput(
            project_id=capture_package["project_id"],
            part_id=capture_package["part_id"],
            capture_package_id=capture_package["capture_package_id"],
            measurement_package_id=measurement_package["measurement_package_id"],
            view_id=view_id,
            source_view_ids=(view_id,),
            coordinate_system="MAT_XY_MM",
            measurements=tuple(normalized),
        )
