from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Any, Mapping

SOLIDWORKS_DIMENSION_RULES_SCHEMA = "mrea.solidworks-dimension-rules.v1"

_DIMENSION_RULES: dict[str, Any] = {
    "schema_version": SOLIDWORKS_DIMENSION_RULES_SCHEMA,
    "distinct_entity_ids": True,
    "types": {
        "DISTANCE": {
            "unit": "mm",
            "entity_type_patterns": [
                ["LINE"],
                ["CIRCLE", "CIRCLE"],
                ["CIRCLE", "ARC"],
                ["ARC", "CIRCLE"],
                ["ARC", "ARC"],
            ],
        },
        "DIAMETER": {
            "unit": "mm",
            "entity_type_patterns": [["CIRCLE"]],
        },
        "RADIUS": {
            "unit": "mm",
            "entity_type_patterns": [["CIRCLE"], ["ARC"]],
        },
        "ANGLE": {
            "unit": "deg",
            "entity_type_patterns": [["LINE", "LINE"]],
            "value": {"exclusive_min": 0.0, "exclusive_max": 180.0},
            "geometry": {
                "non_parallel": True,
                "normalized_cross_min": 1e-10,
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class SolidWorksDimensionSupportDecision:
    """Machine-readable fail-closed decision for one verified dimension."""

    supported: bool
    code: str
    dimension_id: str
    dimension_type: str | None
    unit: str | None
    entity_ids: tuple[str, ...]
    entity_types: tuple[str | None, ...]
    message: str


def build_solidworks_dimension_rules_v1() -> dict[str, Any]:
    """Return the deterministic slice-local dimension-shape capability contract."""

    return deepcopy(_DIMENSION_RULES)


def _decision(
    *,
    supported: bool,
    code: str,
    dimension_id: str,
    dimension_type: str | None,
    unit: str | None,
    entity_ids: tuple[str, ...],
    entity_types: tuple[str | None, ...],
    message: str,
) -> SolidWorksDimensionSupportDecision:
    return SolidWorksDimensionSupportDecision(
        supported=supported,
        code=code,
        dimension_id=dimension_id,
        dimension_type=dimension_type,
        unit=unit,
        entity_ids=entity_ids,
        entity_types=entity_types,
        message=message,
    )


def _line_vector(entity: Mapping[str, Any]) -> tuple[float, float] | None:
    start = entity.get("start")
    end = entity.get("end")
    if not isinstance(start, Mapping) or not isinstance(end, Mapping):
        return None
    try:
        sx = float(start["x"])
        sy = float(start["y"])
        ex = float(end["x"])
        ey = float(end["y"])
    except (KeyError, TypeError, ValueError):
        return None
    values = (sx, sy, ex, ey)
    if not all(isfinite(value) for value in values):
        return None
    return ex - sx, ey - sy


def _normalized_cross(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> float | None:
    first_vector = _line_vector(first)
    second_vector = _line_vector(second)
    if first_vector is None or second_vector is None:
        return None
    r_x, r_y = first_vector
    s_x, s_y = second_vector
    first_length_sq = r_x * r_x + r_y * r_y
    second_length_sq = s_x * s_x + s_y * s_y
    scale = sqrt(first_length_sq * second_length_sq)
    if scale <= 0.0:
        return None
    return abs(r_x * s_y - r_y * s_x) / scale


def evaluate_solidworks_dimension_support_v1(
    dimension: Mapping[str, Any],
    entities_by_id: Mapping[str, Mapping[str, Any]],
) -> SolidWorksDimensionSupportDecision:
    """Evaluate the exact verified-dimension subset before invoking the CAD worker."""

    dimension_id = str(dimension.get("dimension_id", "<unknown>"))
    dimension_type_raw = dimension.get("type")
    dimension_type = str(dimension_type_raw) if dimension_type_raw is not None else None
    unit_raw = dimension.get("unit")
    unit = str(unit_raw) if unit_raw is not None else None
    raw_entity_ids = dimension.get("entity_ids")

    if raw_entity_ids is None:
        entity_ids: tuple[str, ...] = ()
    elif isinstance(raw_entity_ids, (list, tuple)):
        entity_ids = tuple(str(item) for item in raw_entity_ids)
    else:
        return _decision(
            supported=False,
            code="ENTITY_IDS_INVALID",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=(),
            entity_types=(),
            message="dimension entity_ids must be a list/tuple",
        )

    rules = _DIMENSION_RULES["types"]
    if dimension_type not in rules:
        return _decision(
            supported=False,
            code="TYPE_UNSUPPORTED",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=(),
            message=f"dimension type {dimension_type!r} is not supported by the SOLIDWORKS vendor slice",
        )

    rule = rules[dimension_type]
    if unit != rule["unit"]:
        return _decision(
            supported=False,
            code="UNIT_UNSUPPORTED",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=(),
            message=f"{dimension_type} requires canonical unit {rule['unit']!r}; got {unit!r}",
        )

    if not entity_ids:
        return _decision(
            supported=False,
            code="ENTITY_IDS_INVALID",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=(),
            message="dimension requires at least one entity_id",
        )

    if _DIMENSION_RULES["distinct_entity_ids"] and len(set(entity_ids)) != len(entity_ids):
        return _decision(
            supported=False,
            code="ENTITY_IDS_DUPLICATE",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=(),
            message="dimension contains duplicate entity_ids",
        )

    unknown = tuple(entity_id for entity_id in entity_ids if entity_id not in entities_by_id)
    if unknown:
        return _decision(
            supported=False,
            code="ENTITY_UNKNOWN",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=(),
            message=f"dimension references unknown entities: {unknown!r}",
        )

    entity_types = tuple(entities_by_id[entity_id].get("type") for entity_id in entity_ids)
    allowed_patterns = {tuple(pattern) for pattern in rule["entity_type_patterns"]}
    if entity_types not in allowed_patterns:
        return _decision(
            supported=False,
            code="ENTITY_PATTERN_UNSUPPORTED",
            dimension_id=dimension_id,
            dimension_type=dimension_type,
            unit=unit,
            entity_ids=entity_ids,
            entity_types=entity_types,
            message=(
                f"{dimension_type} does not support entity type pattern {entity_types!r}; "
                f"allowed={sorted(allowed_patterns)!r}"
            ),
        )

    value_rule = rule.get("value")
    if value_rule is not None:
        value_raw = dimension.get("value")
        if isinstance(value_raw, bool):
            value = None
        else:
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                value = None
        if value is None or not isfinite(value):
            return _decision(
                supported=False,
                code="VALUE_INVALID",
                dimension_id=dimension_id,
                dimension_type=dimension_type,
                unit=unit,
                entity_ids=entity_ids,
                entity_types=entity_types,
                message=f"{dimension_type} requires a finite numeric value",
            )
        if not value_rule["exclusive_min"] < value < value_rule["exclusive_max"]:
            return _decision(
                supported=False,
                code="VALUE_OUT_OF_RANGE",
                dimension_id=dimension_id,
                dimension_type=dimension_type,
                unit=unit,
                entity_ids=entity_ids,
                entity_types=entity_types,
                message=(
                    f"{dimension_type} requires "
                    f"{value_rule['exclusive_min']} < value < {value_rule['exclusive_max']}"
                ),
            )

    geometry_rule = rule.get("geometry")
    if geometry_rule and geometry_rule.get("non_parallel"):
        normalized_cross = _normalized_cross(
            entities_by_id[entity_ids[0]],
            entities_by_id[entity_ids[1]],
        )
        if normalized_cross is None:
            return _decision(
                supported=False,
                code="GEOMETRY_INVALID",
                dimension_id=dimension_id,
                dimension_type=dimension_type,
                unit=unit,
                entity_ids=entity_ids,
                entity_types=entity_types,
                message=f"{dimension_type} requires two finite non-degenerate LINE entities",
            )
        threshold = float(geometry_rule["normalized_cross_min"])
        if normalized_cross < threshold:
            return _decision(
                supported=False,
                code="GEOMETRY_UNSUPPORTED",
                dimension_id=dimension_id,
                dimension_type=dimension_type,
                unit=unit,
                entity_ids=entity_ids,
                entity_types=entity_types,
                message=f"{dimension_type} requires non-parallel LINE entities",
            )

    return _decision(
        supported=True,
        code="SUPPORTED",
        dimension_id=dimension_id,
        dimension_type=dimension_type,
        unit=unit,
        entity_ids=entity_ids,
        entity_types=entity_types,
        message="dimension is supported by the current fail-closed SOLIDWORKS vendor subset",
    )
