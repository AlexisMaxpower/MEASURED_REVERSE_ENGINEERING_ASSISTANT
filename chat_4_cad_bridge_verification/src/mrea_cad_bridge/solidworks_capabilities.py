from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

SOLIDWORKS_CAPABILITIES_SCHEMA = "mrea.solidworks-capabilities.v1"
SOLIDWORKS_ADAPTER_NAME = "SOLIDWORKS_2026"

_CAPABILITIES: dict[str, Any] = {
    "schema_version": SOLIDWORKS_CAPABILITIES_SCHEMA,
    "adapter_name": SOLIDWORKS_ADAPTER_NAME,
    "geometry_entities": {
        "supported": ["POINT", "LINE", "CIRCLE", "ARC"],
        "unsupported": [],
    },
    "verified_dimensions": {
        "supported": ["DISTANCE", "DIAMETER", "RADIUS", "ANGLE"],
        "units": {"DISTANCE": "mm", "DIAMETER": "mm", "RADIUS": "mm", "ANGLE": "deg"},
    },
    "constraints": {
        "supported": [
            "HORIZONTAL",
            "VERTICAL",
            "PARALLEL",
            "PERPENDICULAR",
            "CONCENTRIC",
            "EQUAL",
            "TANGENT",
        ],
        "unsupported": ["COINCIDENT", "SYMMETRIC"],
        "supported_status": "VERIFIED",
        "rules": {
            "constraint_id_required": True,
            "distinct_entity_ids": True,
            "references_must_exist": True,
            "types": {
                "HORIZONTAL": {"entity_type_patterns": [["LINE"]]},
                "VERTICAL": {"entity_type_patterns": [["LINE"]]},
                "PARALLEL": {"entity_type_patterns": [["LINE", "LINE"]]},
                "PERPENDICULAR": {"entity_type_patterns": [["LINE", "LINE"]]},
                "CONCENTRIC": {
                    "entity_type_patterns": [
                        ["CIRCLE", "CIRCLE"],
                        ["CIRCLE", "ARC"],
                        ["ARC", "CIRCLE"],
                        ["ARC", "ARC"],
                    ]
                },
                "EQUAL": {"entity_type_patterns": [["LINE", "LINE"]]},
                "TANGENT": {
                    "entity_type_patterns": [
                        ["LINE", "CIRCLE"],
                        ["LINE", "ARC"],
                        ["CIRCLE", "LINE"],
                        ["CIRCLE", "CIRCLE"],
                        ["CIRCLE", "ARC"],
                        ["ARC", "LINE"],
                        ["ARC", "CIRCLE"],
                        ["ARC", "ARC"],
                    ]
                },
            },
        },
        "limitations": {
            "EQUAL": "LINE/LINE only",
            "TANGENT": "exactly two LINE/CIRCLE/ARC entities with at least one CIRCLE/ARC; LINE/LINE and POINT participation are rejected",
            "COINCIDENT": "endpoint/sub-entity role is not represented by canonical entity_ids alone",
            "SYMMETRIC": "symmetry axis/sub-entity role is not represented explicitly enough for fail-closed mapping",
        },
    },
    "runtime": {
        "real_host_gate": "EXTERNAL_EVIDENCE_REQUIRED",
        "real_host_status": "UNVERIFIED",
        "production_build_status": "UNVERIFIED",
        "requires_windows_11_x64": True,
        "requires_solidworks_2026": True,
    },
    "protocols": {
        "agent": "mrea.solidworks-agent.v1",
        "host_readiness": "mrea.cad-host-readiness.v1",
        "runtime_evidence": "mrea.cad-runtime-evidence.v1",
        "runtime_inputs": "mrea.solidworks-runtime-inputs.v1",
        "runtime_receipt": "mrea.cad-runtime-receipt.v1",
    },
}


@dataclass(frozen=True, slots=True)
class SolidWorksConstraintSupportDecision:
    """Machine-readable vendor preflight result for one canonical constraint."""

    supported: bool
    code: str
    constraint_id: str
    constraint_type: str | None
    status: str | None
    entity_ids: tuple[str, ...]
    entity_types: tuple[str | None, ...]
    message: str


def build_solidworks_capabilities_v1() -> dict[str, Any]:
    """Return a deterministic, caller-safe snapshot of the current vendor capability boundary."""

    return deepcopy(_CAPABILITIES)


def is_solidworks_constraint_supported_v1(constraint_type: str, *, status: str = "VERIFIED") -> bool:
    """Cheap type/status query; geometry compatibility requires the full preflight evaluator."""

    return (
        status == _CAPABILITIES["constraints"]["supported_status"]
        and constraint_type in _CAPABILITIES["constraints"]["supported"]
    )


def _decision(
    *,
    supported: bool,
    code: str,
    constraint_id: str,
    constraint_type: str | None,
    status: str | None,
    entity_ids: tuple[str, ...],
    entity_types: tuple[str | None, ...],
    message: str,
) -> SolidWorksConstraintSupportDecision:
    return SolidWorksConstraintSupportDecision(
        supported=supported,
        code=code,
        constraint_id=constraint_id,
        constraint_type=constraint_type,
        status=status,
        entity_ids=entity_ids,
        entity_types=entity_types,
        message=message,
    )


def evaluate_solidworks_constraint_support_v1(
    constraint: Mapping[str, Any],
    entities_by_id: Mapping[str, Mapping[str, Any]],
) -> SolidWorksConstraintSupportDecision:
    """Evaluate the fingerprinted fail-closed constraint subset without invoking the CAD worker."""

    constraint_id_raw = constraint.get("constraint_id")
    constraint_id = constraint_id_raw if isinstance(constraint_id_raw, str) else "<unknown>"
    constraint_type_raw = constraint.get("type")
    constraint_type = str(constraint_type_raw) if constraint_type_raw is not None else None
    status_raw = constraint.get("status")
    status = str(status_raw) if status_raw is not None else None
    raw_entity_ids = constraint.get("entity_ids")
    rules = _CAPABILITIES["constraints"]["rules"]

    if rules["constraint_id_required"] and (
        not isinstance(constraint_id_raw, str) or not constraint_id_raw
    ):
        return _decision(
            supported=False,
            code="CONSTRAINT_ID_INVALID",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=(),
            entity_types=(),
            message="constraint_id must be a non-empty string",
        )

    if raw_entity_ids is None:
        entity_ids: tuple[str, ...] = ()
    elif isinstance(raw_entity_ids, (list, tuple)):
        entity_ids = tuple(str(item) for item in raw_entity_ids)
    else:
        return _decision(
            supported=False,
            code="ENTITY_IDS_INVALID",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=(),
            entity_types=(),
            message="constraint entity_ids must be a list/tuple",
        )

    if status != _CAPABILITIES["constraints"]["supported_status"]:
        return _decision(
            supported=False,
            code="STATUS_NOT_VERIFIED",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=entity_ids,
            entity_types=(),
            message=f"constraint status must be VERIFIED; got {status!r}",
        )

    type_rules = rules["types"]
    if constraint_type not in type_rules:
        return _decision(
            supported=False,
            code="TYPE_UNSUPPORTED",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=entity_ids,
            entity_types=(),
            message=f"constraint type {constraint_type!r} is not supported by the SOLIDWORKS vendor slice",
        )

    if rules["distinct_entity_ids"] and len(set(entity_ids)) != len(entity_ids):
        return _decision(
            supported=False,
            code="ENTITY_IDS_DUPLICATE",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=entity_ids,
            entity_types=(),
            message="constraint contains duplicate entity_ids",
        )

    if rules["references_must_exist"]:
        unknown = tuple(entity_id for entity_id in entity_ids if entity_id not in entities_by_id)
        if unknown:
            return _decision(
                supported=False,
                code="ENTITY_UNKNOWN",
                constraint_id=constraint_id,
                constraint_type=constraint_type,
                status=status,
                entity_ids=entity_ids,
                entity_types=(),
                message=f"constraint references unknown entities: {unknown!r}",
            )

    entity_types = tuple(entities_by_id[entity_id].get("type") for entity_id in entity_ids)
    patterns = tuple(
        tuple(pattern)
        for pattern in type_rules[constraint_type]["entity_type_patterns"]
    )
    valid_arities = {len(pattern) for pattern in patterns}
    if len(entity_ids) not in valid_arities:
        return _decision(
            supported=False,
            code="ARITY_UNSUPPORTED",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=entity_ids,
            entity_types=entity_types,
            message=(
                f"{constraint_type} requires entity arity in "
                f"{sorted(valid_arities)!r}"
            ),
        )

    if entity_types not in patterns:
        return _decision(
            supported=False,
            code="GEOMETRY_UNSUPPORTED",
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            status=status,
            entity_ids=entity_ids,
            entity_types=entity_types,
            message=(
                f"{constraint_type} does not support entity type pattern "
                f"{entity_types!r}"
            ),
        )

    return _decision(
        supported=True,
        code="SUPPORTED",
        constraint_id=constraint_id,
        constraint_type=constraint_type,
        status=status,
        entity_ids=entity_ids,
        entity_types=entity_types,
        message="constraint is supported by the current fail-closed SOLIDWORKS vendor subset",
    )
