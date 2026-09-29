from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .model import ArcEntity, CadSketch, CircleEntity, LineEntity, Point2D, PointEntity
from .verification import ExpectedDimension, VerificationReport, VerificationStatus

SCHEMA_VERSION_SKETCH = "mrea.sketch-package.v1"
SCHEMA_VERSION_CAD_PACKAGE = "mrea.cad-package.v1"
SCHEMA_VERSION_VERIFICATION = "mrea.cad-verification.v1"
COORDINATE_SYSTEM = "MAT_XY_MM"
DEFAULT_LENGTH_TOLERANCE_MM = 1e-6
DEFAULT_ANGLE_TOLERANCE_DEG = 1e-6


class ContractMappingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MappedSketchPackage:
    sketch_package_id: str
    project_id: str
    part_id: str
    view_id: str
    sketch: CadSketch
    expected_dimensions: tuple[ExpectedDimension, ...]
    entity_contracts: tuple[Mapping[str, Any], ...]
    dimensions: tuple[Mapping[str, Any], ...]
    constraints: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    source_view_ids: tuple[str, ...]


def _point(raw: Mapping[str, Any]) -> Point2D:
    try:
        return Point2D(x=float(raw["x"]), y=float(raw["y"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractMappingError(f"invalid canonical Point2D: {raw!r}") from exc


def _map_entity(raw: Mapping[str, Any]):
    entity_type = raw.get("type")
    entity_id = raw.get("entity_id")
    if not isinstance(entity_id, str) or not entity_id:
        raise ContractMappingError("canonical entity_id must be a non-empty string")

    try:
        if entity_type == "POINT":
            return PointEntity(entity_id=entity_id, point=_point(raw["point"]))
        if entity_type == "LINE":
            return LineEntity(
                entity_id=entity_id,
                start=_point(raw["start"]),
                end=_point(raw["end"]),
            )
        if entity_type == "CIRCLE":
            return CircleEntity(
                entity_id=entity_id,
                center=_point(raw["center"]),
                radius=float(raw["radius"]),
            )
        if entity_type == "ARC":
            return ArcEntity(
                entity_id=entity_id,
                center=_point(raw["center"]),
                radius=float(raw["radius"]),
                start_angle_deg=float(raw["start_angle_deg"]),
                end_angle_deg=float(raw["end_angle_deg"]),
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractMappingError(
            f"invalid canonical {entity_type!r} entity {entity_id!r}"
        ) from exc

    raise ContractMappingError(
        f"unsupported canonical SketchPackage v1 entity type: {entity_type!r}; "
        "unsupported geometry must remain in SketchPackage.unresolved"
    )


def _tolerance_for_unit(unit: str) -> float:
    if unit == "mm":
        return DEFAULT_LENGTH_TOLERANCE_MM
    if unit == "deg":
        return DEFAULT_ANGLE_TOLERANCE_DEG
    raise ContractMappingError(f"unsupported canonical dimension unit: {unit!r}")


def _required_string(package: Mapping[str, Any], field: str) -> str:
    value = package.get(field)
    if not isinstance(value, str) or not value:
        raise ContractMappingError(f"{field} must be a non-empty string")
    return value


def map_sketch_package_v1(package: Mapping[str, Any]) -> MappedSketchPackage:
    if package.get("schema_version") != SCHEMA_VERSION_SKETCH:
        raise ContractMappingError(
            f"expected schema_version={SCHEMA_VERSION_SKETCH!r}, "
            f"got {package.get('schema_version')!r}"
        )
    if package.get("coordinate_system") != COORDINATE_SYSTEM:
        raise ContractMappingError(
            f"expected coordinate_system={COORDINATE_SYSTEM!r}, "
            f"got {package.get('coordinate_system')!r}"
        )

    try:
        entities_raw = package["entities"]
        dimensions_raw = package["dimensions"]
        constraints_raw = package["constraints"]
        unresolved_raw = package["unresolved"]
        source_view_ids_raw = package["source_view_ids"]
    except KeyError as exc:
        raise ContractMappingError(
            f"missing canonical SketchPackage field: {exc.args[0]}"
        ) from exc

    if not all(
        isinstance(value, list)
        for value in (
            entities_raw,
            dimensions_raw,
            constraints_raw,
            unresolved_raw,
            source_view_ids_raw,
        )
    ):
        raise ContractMappingError(
            "entities, dimensions, constraints, unresolved and source_view_ids must be arrays"
        )

    entity_contracts = tuple(dict(entity) for entity in entities_raw)
    entities = tuple(_map_entity(entity) for entity in entities_raw)

    dimensions = tuple(dict(dimension) for dimension in dimensions_raw)
    expected_dimensions: list[ExpectedDimension] = []
    for dimension in dimensions_raw:
        if not dimension.get("verified", False):
            continue

        dimension_id = dimension.get("dimension_id")
        if not isinstance(dimension_id, str) or not dimension_id:
            raise ContractMappingError(
                "verified dimension must have a non-empty dimension_id"
            )

        measurement_id = dimension.get("measurement_id")
        if measurement_id is not None and (
            not isinstance(measurement_id, str) or not measurement_id
        ):
            raise ContractMappingError(
                "measurement_id must be null or a non-empty string"
            )

        unit = dimension.get("unit")
        try:
            expected_value = float(dimension["value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractMappingError(
                f"verified dimension {dimension_id!r} has invalid value"
            ) from exc

        expected_dimensions.append(
            ExpectedDimension(
                dimension_id=dimension_id,
                measurement_id=measurement_id,
                expected_value=expected_value,
                unit=unit,
                tolerance=_tolerance_for_unit(unit),
            )
        )

    return MappedSketchPackage(
        sketch_package_id=_required_string(package, "sketch_package_id"),
        project_id=_required_string(package, "project_id"),
        part_id=_required_string(package, "part_id"),
        view_id=_required_string(package, "view_id"),
        sketch=CadSketch(entities=entities, units="mm"),
        expected_dimensions=tuple(expected_dimensions),
        entity_contracts=entity_contracts,
        dimensions=dimensions,
        constraints=tuple(dict(item) for item in constraints_raw),
        unresolved=tuple(dict(item) for item in unresolved_raw),
        source_view_ids=tuple(str(item) for item in source_view_ids_raw),
    )


def build_cad_package_v1(
    *,
    cad_package_id: str,
    sketch_package_id: str,
    adapter: str,
    artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    for name, value in (
        ("cad_package_id", cad_package_id),
        ("sketch_package_id", sketch_package_id),
        ("adapter", adapter),
    ):
        if not value:
            raise ContractMappingError(f"{name} must not be empty")

    return {
        "schema_version": SCHEMA_VERSION_CAD_PACKAGE,
        "cad_package_id": cad_package_id,
        "sketch_package_id": sketch_package_id,
        "adapter": adapter,
        "artifacts": [dict(artifact) for artifact in artifacts],
    }


def build_cad_verification_report_v1(
    *,
    report_id: str,
    cad_package_id: str,
    sketch_package_id: str,
    report: VerificationReport,
) -> dict[str, Any]:
    for name, value in (
        ("report_id", report_id),
        ("cad_package_id", cad_package_id),
        ("sketch_package_id", sketch_package_id),
    ):
        if not value:
            raise ContractMappingError(f"{name} must not be empty")

    items = [
        {
            "dimension_id": result.dimension_id,
            "measurement_id": result.measurement_id,
            "expected": result.expected_value,
            "actual": result.actual_value,
            "unit": result.unit,
            "tolerance": result.tolerance,
            "difference": result.difference,
            "status": result.status.value,
        }
        for result in report.results
    ]

    overall_status = (
        "VERIFIED"
        if all(result.status is VerificationStatus.VERIFIED for result in report.results)
        else "FAILED"
    )

    return {
        "schema_version": SCHEMA_VERSION_VERIFICATION,
        "report_id": report_id,
        "cad_package_id": cad_package_id,
        "sketch_package_id": sketch_package_id,
        "policy": {
            "kind": "NUMERICAL_TRANSFER",
            "default_length_tolerance_mm": DEFAULT_LENGTH_TOLERANCE_MM,
            "default_angle_tolerance_deg": DEFAULT_ANGLE_TOLERANCE_DEG,
        },
        "items": items,
        "overall_status": overall_status,
    }
