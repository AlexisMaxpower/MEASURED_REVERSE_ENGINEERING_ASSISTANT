from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

RUNTIME_RECEIPT_SCHEMA = "mrea.cad-runtime-receipt.v1"
_RUNTIME_EVIDENCE_SCHEMA = "mrea.cad-runtime-evidence.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_RUNTIME_STATUSES = {"VERIFIED", "FAILED", "UNVERIFIED"}


class CadRuntimeReceiptError(ValueError):
    """Fail-closed audit-receipt error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if not code:
            raise ValueError("receipt error code must not be empty")
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_NON_CANONICAL_JSON",
            "runtime receipt inputs must not contain NaN or infinity",
        )
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_non_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_non_finite(item)


def canonical_json_bytes(value: Any) -> bytes:
    """Encode finite JSON deterministically for content-addressed evidence."""
    _reject_non_finite(value)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_NON_CANONICAL_JSON",
            "runtime receipt inputs must be JSON-compatible",
        ) from exc
    return text.encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_FIELD_INVALID",
            f"{field} must be a JSON object",
            details={"field": field},
        )
    return value


def _require_nonempty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_FIELD_INVALID",
            f"{field} must be a non-empty string",
            details={"field": field},
        )
    return value


def _normalize_artifacts(cad_package: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if cad_package is None:
        return []
    raw = cad_package.get("artifacts", [])
    if not isinstance(raw, list):
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_ARTIFACTS_INVALID",
            "CADPackage artifacts must be an array",
        )

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_ARTIFACTS_INVALID",
                "CADPackage artifact entries must be objects",
            )
        artifact_id = _require_nonempty_string(item.get("artifact_id"), field="artifact_id")
        kind = _require_nonempty_string(item.get("kind"), field="kind")
        uri = _require_nonempty_string(item.get("uri"), field="uri")
        digest = item.get("sha256")
        if artifact_id in seen:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_ARTIFACT_ID_DUPLICATE",
                f"duplicate artifact_id {artifact_id!r}",
            )
        seen.add(artifact_id)
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest.lower()):
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_ARTIFACT_HASH_INVALID",
                f"artifact {artifact_id!r} requires a 64-character SHA-256 digest",
            )
        normalized.append(
            {
                "artifact_id": artifact_id,
                "kind": kind,
                "uri": uri,
                "sha256": digest.lower(),
            }
        )
    normalized.sort(key=lambda item: item["artifact_id"])
    return normalized


def _validate_cross_identity(
    *,
    sketch_package: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    cad_package: Mapping[str, Any] | None,
    cad_verification_report: Mapping[str, Any] | None,
) -> tuple[str, str, str, str | None]:
    sketch_id = _require_nonempty_string(
        sketch_package.get("sketch_package_id"), field="sketch_package.sketch_package_id"
    )
    if runtime_evidence.get("schema_version") != _RUNTIME_EVIDENCE_SCHEMA:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_EVIDENCE_SCHEMA_MISMATCH",
            "runtime evidence schema is not mrea.cad-runtime-evidence.v1",
        )
    if runtime_evidence.get("sketch_package_id") != sketch_id:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_SKETCH_ID_MISMATCH",
            "runtime evidence points to a different SketchPackage",
        )
    adapter = _require_nonempty_string(
        runtime_evidence.get("adapter_name"), field="runtime_evidence.adapter_name"
    )
    runtime_status = _require_nonempty_string(
        runtime_evidence.get("status"), field="runtime_evidence.status"
    )
    if runtime_status not in _ALLOWED_RUNTIME_STATUSES:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_STATUS_INVALID",
            f"unsupported runtime evidence status {runtime_status!r}",
        )

    cad_id: str | None = None
    verification_status: str | None = None
    if cad_package is not None:
        cad_id = _require_nonempty_string(
            cad_package.get("cad_package_id"), field="cad_package.cad_package_id"
        )
        if cad_package.get("sketch_package_id") != sketch_id:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_CAD_SKETCH_ID_MISMATCH",
                "CADPackage points to a different SketchPackage",
            )
        if cad_package.get("adapter") != adapter:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_CAD_ADAPTER_MISMATCH",
                "CADPackage adapter disagrees with runtime evidence",
            )

    if cad_verification_report is not None:
        if cad_verification_report.get("sketch_package_id") != sketch_id:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_REPORT_SKETCH_ID_MISMATCH",
                "CADVerificationReport points to a different SketchPackage",
            )
        if cad_id is None:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_CAD_PACKAGE_MISSING",
                "CADVerificationReport cannot be receipt-bound without CADPackage",
            )
        if cad_verification_report.get("cad_package_id") != cad_id:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_REPORT_CAD_ID_MISMATCH",
                "CADVerificationReport points to a different CADPackage",
            )
        verification_status = _require_nonempty_string(
            cad_verification_report.get("overall_status"),
            field="cad_verification_report.overall_status",
        )

    if runtime_status == "VERIFIED":
        if cad_package is None or cad_verification_report is None:
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_VERIFIED_CHAIN_INCOMPLETE",
                "VERIFIED runtime evidence requires CADPackage and CADVerificationReport",
            )
        if verification_status != "VERIFIED":
            raise CadRuntimeReceiptError(
                "RUNTIME_RECEIPT_VERIFICATION_STATUS_MISMATCH",
                "VERIFIED runtime evidence requires canonical verification status VERIFIED",
            )
    return sketch_id, adapter, runtime_status, verification_status


def build_runtime_receipt_v1(
    *,
    sketch_package: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    cad_package: Mapping[str, Any] | None = None,
    cad_verification_report: Mapping[str, Any] | None = None,
    source_runtime_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sketch_package = _require_mapping(sketch_package, field="sketch_package")
    runtime_evidence = _require_mapping(runtime_evidence, field="runtime_evidence")
    if cad_package is not None:
        cad_package = _require_mapping(cad_package, field="cad_package")
    if cad_verification_report is not None:
        cad_verification_report = _require_mapping(
            cad_verification_report, field="cad_verification_report"
        )
    if source_runtime_inputs is not None:
        source_runtime_inputs = _require_mapping(
            source_runtime_inputs, field="source_runtime_inputs"
        )

    sketch_id, adapter, runtime_status, verification_status = _validate_cross_identity(
        sketch_package=sketch_package,
        runtime_evidence=runtime_evidence,
        cad_package=cad_package,
        cad_verification_report=cad_verification_report,
    )

    body: dict[str, Any] = {
        "schema_version": RUNTIME_RECEIPT_SCHEMA,
        "sketch_package_id": sketch_id,
        "adapter_name": adapter,
        "runtime_status": runtime_status,
        "verification_status": verification_status,
        "object_hashes": {
            "sketch_package_sha256": sha256_json(sketch_package),
            "runtime_evidence_sha256": sha256_json(runtime_evidence),
            "cad_package_sha256": sha256_json(cad_package) if cad_package is not None else None,
            "cad_verification_report_sha256": (
                sha256_json(cad_verification_report)
                if cad_verification_report is not None
                else None
            ),
            "source_runtime_inputs_sha256": (
                sha256_json(source_runtime_inputs)
                if source_runtime_inputs is not None
                else None
            ),
        },
        "artifacts": _normalize_artifacts(cad_package),
    }
    body["receipt_sha256"] = sha256_json(body)
    return body


def verify_runtime_receipt_v1(
    *,
    receipt: Mapping[str, Any],
    sketch_package: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    cad_package: Mapping[str, Any] | None = None,
    cad_verification_report: Mapping[str, Any] | None = None,
    source_runtime_inputs: Mapping[str, Any] | None = None,
) -> None:
    receipt = _require_mapping(receipt, field="receipt")
    if receipt.get("schema_version") != RUNTIME_RECEIPT_SCHEMA:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_SCHEMA_MISMATCH",
            "runtime receipt schema mismatch",
        )
    supplied_hash = receipt.get("receipt_sha256")
    if not isinstance(supplied_hash, str) or not _SHA256_RE.fullmatch(supplied_hash.lower()):
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_HASH_INVALID",
            "receipt_sha256 must be a 64-character SHA-256 digest",
        )
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if sha256_json(unsigned) != supplied_hash.lower():
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_SELF_HASH_MISMATCH",
            "runtime receipt content does not match receipt_sha256",
        )

    expected = build_runtime_receipt_v1(
        sketch_package=sketch_package,
        runtime_evidence=runtime_evidence,
        cad_package=cad_package,
        cad_verification_report=cad_verification_report,
        source_runtime_inputs=source_runtime_inputs,
    )
    if dict(receipt) != expected:
        raise CadRuntimeReceiptError(
            "RUNTIME_RECEIPT_OBJECT_HASH_MISMATCH",
            "runtime receipt does not match the supplied evidence objects",
        )
