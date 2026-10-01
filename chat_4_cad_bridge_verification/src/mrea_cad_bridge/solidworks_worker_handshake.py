from __future__ import annotations

import hashlib
import json
from typing import Any

from .solidworks_capabilities import build_solidworks_capabilities_v1


def build_solidworks_worker_capability_projection_v1() -> dict[str, Any]:
    """Return the exact capability subset that must stay in sync with the C# worker."""

    capabilities = build_solidworks_capabilities_v1()
    return {
        "schema_version": capabilities["schema_version"],
        "adapter_name": capabilities["adapter_name"],
        "geometry_entities": capabilities["geometry_entities"],
        "verified_dimensions": capabilities["verified_dimensions"],
        "constraints": capabilities["constraints"],
        "protocols": {"agent": capabilities["protocols"]["agent"]},
    }


def solidworks_worker_capabilities_sha256_v1() -> str:
    """Fingerprint the Python/C# compatibility surface using canonical JSON."""

    canonical = json.dumps(
        build_solidworks_worker_capability_projection_v1(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


SOLIDWORKS_WORKER_CAPABILITIES_SHA256 = solidworks_worker_capabilities_sha256_v1()
