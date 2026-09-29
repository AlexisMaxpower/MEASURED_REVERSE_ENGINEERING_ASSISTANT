from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .models import AnchorRef, MeasurementRef, Point2D

_HOMOGRAPHY_EPSILON = 1e-12


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


def _as_finite_number(value: object, *, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not isfinite(number):
        raise ValueError(f"{field_name} must be a finite number")
    return number


def _homography_determinant(values: tuple[float, ...]) -> float:
    a, b, c, d, e, f, g, h, i = values
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _validated_image_to_mat_homography(view: dict) -> tuple[float, ...]:
    calibration = view.get("calibration")
    if not isinstance(calibration, dict):
        raise ValueError("IMAGE_PX anchors require view calibration")
    if calibration.get("coordinate_system") != "MAT_XY_MM":
        raise ValueError("IMAGE_PX anchors require MAT_XY_MM calibration")

    raw = calibration.get("homography")
    if not isinstance(raw, (list, tuple)) or len(raw) != 9:
        raise ValueError("IMAGE_PX anchors require a 3x3 homography")

    values = tuple(
        _as_finite_number(value, field_name=f"homography[{index}]")
        for index, value in enumerate(raw)
    )
    if abs(_homography_determinant(values)) <= _HOMOGRAPHY_EPSILON:
        raise ValueError("IMAGE_PX homography is degenerate")
    return values


def _apply_homography(point: Point2D, homography: tuple[float, ...]) -> Point2D:
    h = homography
    out_x = h[0] * point.x + h[1] * point.y + h[2]
    out_y = h[3] * point.x + h[4] * point.y + h[5]
    out_w = h[6] * point.x + h[7] * point.y + h[8]

    if not all(isfinite(value) for value in (out_x, out_y, out_w)):
        raise ValueError("homography produced a non-finite homogeneous point")
    if abs(out_w) <= _HOMOGRAPHY_EPSILON:
        raise ValueError("homography produced a degenerate homogeneous divisor")

    normalized_x = out_x / out_w
    normalized_y = out_y / out_w
    if not isfinite(normalized_x) or not isfinite(normalized_y):
        raise ValueError("homography produced a non-finite MAT_XY_MM point")
    return Point2D(normalized_x, normalized_y)


class CanonicalInputAdapter:
    """Adapter from Integrator-owned v1 dictionaries into Chat 3 internal models.

    The internal geometry boundary is always MAT_XY_MM. Canonical anchors already in
    MAT_XY_MM pass through. IMAGE_PX anchors are normalized with the matching view's
    IMAGE_PX -> MAT_XY_MM homography after reference-frame verification.
    """

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

        clean_reference = view.get("clean_reference_frame")
        clean_reference_id = (
            clean_reference.get("artifact_id")
            if isinstance(clean_reference, dict)
            else None
        )
        homography: tuple[float, ...] | None = None

        normalized: list[MeasurementRef] = []
        for item in measurement_package.get("measurements", []):
            if item.get("view_id") != view_id:
                continue
            anchors: list[AnchorRef] = []
            for anchor in item.get("anchors", []):
                if anchor.get("view_id") != view_id:
                    raise ValueError("measurement anchor belongs to a different view")

                coordinate_space = anchor.get("coordinate_space")
                raw_point = Point2D(
                    _as_finite_number(anchor.get("x"), field_name="anchor.x"),
                    _as_finite_number(anchor.get("y"), field_name="anchor.y"),
                )

                if coordinate_space == "MAT_XY_MM":
                    point = raw_point
                elif coordinate_space == "IMAGE_PX":
                    reference_frame_id = anchor.get("reference_frame_id")
                    if not isinstance(clean_reference_id, str) or not clean_reference_id:
                        raise ValueError(
                            "IMAGE_PX anchors require a clean reference frame artifact_id"
                        )
                    if reference_frame_id != clean_reference_id:
                        raise ValueError(
                            "IMAGE_PX anchor reference_frame_id does not match "
                            "the view clean reference frame"
                        )
                    if homography is None:
                        homography = _validated_image_to_mat_homography(view)
                    point = _apply_homography(raw_point, homography)
                else:
                    raise ValueError(
                        f"unsupported anchor coordinate_space: {coordinate_space!r}"
                    )

                anchors.append(
                    AnchorRef(
                        anchor_id=anchor["anchor_id"],
                        point=point,
                        feature_id=anchor.get("feature_id"),
                        reference_frame_id=anchor.get("reference_frame_id"),
                        source_coordinate_space=coordinate_space,
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
            measurements=tuple(sorted(normalized, key=lambda item: item.measurement_id)),
        )
