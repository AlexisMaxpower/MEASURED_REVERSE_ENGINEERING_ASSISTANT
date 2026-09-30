from __future__ import annotations

from copy import deepcopy
from typing import Any

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
        ],
        "unsupported": ["COINCIDENT", "TANGENT", "SYMMETRIC"],
        "supported_status": "VERIFIED",
        "limitations": {
            "EQUAL": "LINE/LINE only",
            "COINCIDENT": "endpoint/sub-entity role is not represented by canonical entity_ids alone",
            "TANGENT": "SOLIDWORKS supports sgTANGENT, but the current MREA worker has not implemented and host-validated it",
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


def build_solidworks_capabilities_v1() -> dict[str, Any]:
    """Return a deterministic, caller-safe snapshot of the current vendor capability boundary."""

    return deepcopy(_CAPABILITIES)


def is_solidworks_constraint_supported_v1(constraint_type: str, *, status: str = "VERIFIED") -> bool:
    """Cheap capability query; geometry compatibility is still enforced by vendor preflight."""

    return (
        status == _CAPABILITIES["constraints"]["supported_status"]
        and constraint_type in _CAPABILITIES["constraints"]["supported"]
    )
