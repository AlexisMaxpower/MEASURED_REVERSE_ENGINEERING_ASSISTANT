from __future__ import annotations

import hashlib
import json

from .solidworks_capabilities import build_solidworks_capabilities_v1


def solidworks_constraint_capabilities_sha256_v1() -> str:
    """Fingerprint the exact Python-side constraint capability contract."""

    constraints = build_solidworks_capabilities_v1()["constraints"]
    canonical = json.dumps(
        constraints,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256 = solidworks_constraint_capabilities_sha256_v1()
