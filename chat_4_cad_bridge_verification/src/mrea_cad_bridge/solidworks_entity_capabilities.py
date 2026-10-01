from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

SOLIDWORKS_ENTITY_RULES_SCHEMA = "mrea.solidworks-entity-rules.v1"

_ENTITY_RULES: dict[str, Any] = {
    "schema_version": SOLIDWORKS_ENTITY_RULES_SCHEMA,
    "point_coordinates": {"fields": ["x", "y"], "finite": True},
    "types": {
        "POINT": {"required_points": ["point"]},
        "LINE": {
            "required_points": ["start", "end"],
            "length_squared_mm2": {"exclusive_min": 1e-24},
        },
        "CIRCLE": {
            "required_points": ["center"],
            "radius_mm": {"exclusive_min": 0.0},
        },
        "ARC": {
            "required_points": ["center"],
            "radius_mm": {"exclusive_min": 0.0},
            "angles_deg": {
                "finite": ["start_angle_deg", "end_angle_deg"],
                "positive_modulo_deg": 360.0,
                "span_min_inclusive": 1e-12,
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class SolidWorksEntitySupportDecision:
    """Machine-readable fail-closed decision for one vendor geometry entity."""

    supported: bool
    code: str
    entity_id: str
    entity_type: str | None
    message: str


def build_solidworks_entity_rules_v1() -> dict[str, Any]:
    """Return the deterministic slice-local entity-geometry capability contract."""

    return deepcopy(_ENTITY_RULES)


def _decision(
    *,
    supported: bool,
    code: str,
    entity_id: str,
    entity_type: str | None,
    message: str,
) -> SolidWorksEntitySupportDecision:
    return SolidWorksEntitySupportDecision(
        supported=supported,
        code=code,
        entity_id=entity_id,
        entity_type=entity_type,
        message=message,
    )


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _point(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, Mapping):
        return None
    x = _finite_number(raw.get("x"))
    y = _finite_number(raw.get("y"))
    if x is None or y is None:
        return None
    return x, y


def _positive_modulo(value: float, modulo: float) -> float:
    result = value % modulo
    return result + modulo if result < 0.0 else result


def evaluate_solidworks_entity_support_v1(
    entity: Mapping[str, Any],
) -> SolidWorksEntitySupportDecision:
    """Evaluate geometry validity required by the real SOLIDWORKS worker before COM startup."""

    entity_id_raw = entity.get("entity_id")
    entity_id = entity_id_raw if isinstance(entity_id_raw, str) else "<unknown>"
    entity_type_raw = entity.get("type")
    entity_type = str(entity_type_raw) if entity_type_raw is not None else None

    if not isinstance(entity_id_raw, str) or not entity_id_raw:
        return _decision(
            supported=False,
            code="ENTITY_ID_INVALID",
            entity_id=entity_id,
            entity_type=entity_type,
            message="entity_id must be a non-empty string",
        )

    rules = _ENTITY_RULES["types"]
    if entity_type not in rules:
        return _decision(
            supported=False,
            code="TYPE_UNSUPPORTED",
            entity_id=entity_id,
            entity_type=entity_type,
            message=f"entity type {entity_type!r} is not supported by the SOLIDWORKS vendor slice",
        )

    rule = rules[entity_type]
    points: dict[str, tuple[float, float]] = {}
    for field in rule.get("required_points", ()):
        parsed = _point(entity.get(field))
        if parsed is None:
            return _decision(
                supported=False,
                code="POINT_INVALID",
                entity_id=entity_id,
                entity_type=entity_type,
                message=f"{entity_type} requires finite {field}.x/{field}.y coordinates",
            )
        points[field] = parsed

    if entity_type == "LINE":
        start_x, start_y = points["start"]
        end_x, end_y = points["end"]
        dx = end_x - start_x
        dy = end_y - start_y
        length_squared = dx * dx + dy * dy
        minimum = float(rule["length_squared_mm2"]["exclusive_min"])
        if not length_squared > minimum:
            return _decision(
                supported=False,
                code="GEOMETRY_DEGENERATE",
                entity_id=entity_id,
                entity_type=entity_type,
                message=(
                    "LINE endpoints are too close for the SOLIDWORKS worker; "
                    f"length_squared_mm2 must be > {minimum:g}"
                ),
            )

    if entity_type in {"CIRCLE", "ARC"}:
        radius = _finite_number(entity.get("radius"))
        minimum = float(rule["radius_mm"]["exclusive_min"])
        if radius is None or not radius > minimum:
            return _decision(
                supported=False,
                code="RADIUS_INVALID",
                entity_id=entity_id,
                entity_type=entity_type,
                message=f"{entity_type} radius must be finite and > {minimum:g} mm",
            )

    if entity_type == "ARC":
        angle_rule = rule["angles_deg"]
        start = _finite_number(entity.get("start_angle_deg"))
        end = _finite_number(entity.get("end_angle_deg"))
        if start is None or end is None:
            return _decision(
                supported=False,
                code="ANGLE_INVALID",
                entity_id=entity_id,
                entity_type=entity_type,
                message="ARC start_angle_deg/end_angle_deg must be finite",
            )
        modulo = float(angle_rule["positive_modulo_deg"])
        span = _positive_modulo(end - start, modulo)
        minimum_span = float(angle_rule["span_min_inclusive"])
        if span < minimum_span:
            return _decision(
                supported=False,
                code="GEOMETRY_DEGENERATE",
                entity_id=entity_id,
                entity_type=entity_type,
                message=(
                    "ARC start/end angles resolve to a zero/full-circle span; "
                    "use CIRCLE instead"
                ),
            )

    return _decision(
        supported=True,
        code="SUPPORTED",
        entity_id=entity_id,
        entity_type=entity_type,
        message="entity is supported by the current fail-closed SOLIDWORKS vendor subset",
    )
