from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .vendor import CadAdapterError

RUNTIME_EVIDENCE_SCHEMA = "mrea.cad-runtime-evidence.v1"
HOST_READINESS_SCHEMA = "mrea.cad-host-readiness.v1"
_NATIVE_SOLIDWORKS_KIND = "SOLIDWORKS_PART"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ReadinessCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"


class HostReadinessStatus(str, Enum):
    READY = "READY"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


class RuntimeEvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostic:
    code: str
    stage: str
    message: str
    severity: str = "ERROR"
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("diagnostic code must not be empty")
        if not self.stage:
            raise ValueError("diagnostic stage must not be empty")
        if not self.message:
            raise ValueError("diagnostic message must not be empty")
        if self.severity not in {"ERROR", "WARNING", "INFO"}:
            raise ValueError(f"unsupported diagnostic severity: {self.severity!r}")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "stage": self.stage,
            "message": self.message,
            "severity": self.severity,
        }
        if self.details:
            result["details"] = dict(self.details)
        return result


@dataclass(frozen=True, slots=True)
class HostReadinessCheck:
    code: str
    status: ReadinessCheckStatus
    message: str
    required: bool = True
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("host readiness check code must not be empty")
        if not self.message:
            raise ValueError("host readiness check message must not be empty")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "status": self.status.value,
            "message": self.message,
            "required": self.required,
        }
        if self.details:
            result["details"] = dict(self.details)
        return result


@dataclass(frozen=True, slots=True)
class HostReadinessReport:
    adapter_name: str
    checks: tuple[HostReadinessCheck, ...]

    def __post_init__(self) -> None:
        if not self.adapter_name:
            raise ValueError("adapter_name must not be empty")
        codes = [check.code for check in self.checks]
        if len(codes) != len(set(codes)):
            raise ValueError("host readiness check codes must be unique")

    @property
    def status(self) -> HostReadinessStatus:
        required = tuple(check for check in self.checks if check.required)
        if any(check.status is ReadinessCheckStatus.FAIL for check in required):
            return HostReadinessStatus.FAILED
        if any(check.status is ReadinessCheckStatus.UNVERIFIED for check in required):
            return HostReadinessStatus.UNVERIFIED
        return HostReadinessStatus.READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HOST_READINESS_SCHEMA,
            "adapter_name": self.adapter_name,
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
        }


def parse_host_readiness_report(payload: Mapping[str, Any]) -> HostReadinessReport:
    if payload.get("schema_version") != HOST_READINESS_SCHEMA:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_SCHEMA_MISMATCH",
            f"expected {HOST_READINESS_SCHEMA!r}, got {payload.get('schema_version')!r}",
            stage="HOST_PREFLIGHT",
        )

    adapter_name = payload.get("adapter_name")
    raw_checks = payload.get("checks")
    if not isinstance(adapter_name, str) or not adapter_name:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_ADAPTER_MISSING",
            "host-readiness payload requires adapter_name",
            stage="HOST_PREFLIGHT",
        )
    if not isinstance(raw_checks, list):
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_CHECKS_INVALID",
            "host-readiness payload requires a checks array",
            stage="HOST_PREFLIGHT",
        )

    checks: list[HostReadinessCheck] = []
    try:
        for item in raw_checks:
            if not isinstance(item, Mapping):
                raise TypeError("check must be an object")
            checks.append(
                HostReadinessCheck(
                    code=str(item["code"]),
                    status=ReadinessCheckStatus(str(item["status"])),
                    message=str(item["message"]),
                    required=bool(item.get("required", True)),
                    details=(
                        dict(item["details"])
                        if isinstance(item.get("details"), Mapping)
                        else None
                    ),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_CHECKS_INVALID",
            "host-readiness checks contain invalid data",
            stage="HOST_PREFLIGHT",
        ) from exc

    report = HostReadinessReport(adapter_name=adapter_name, checks=tuple(checks))
    reported_status = payload.get("status")
    if reported_status is not None and reported_status != report.status.value:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_STATUS_MISMATCH",
            "reported host-readiness status disagrees with check results",
            stage="HOST_PREFLIGHT",
            details={
                "reported": reported_status,
                "computed": report.status.value,
            },
        )
    return report


def parse_runtime_diagnostic(payload: Mapping[str, Any]) -> RuntimeDiagnostic:
    try:
        details = payload.get("details")
        if details is not None and not isinstance(details, Mapping):
            raise TypeError("diagnostic details must be an object")
        return RuntimeDiagnostic(
            code=str(payload["code"]),
            stage=str(payload["stage"]),
            message=str(payload["message"]),
            severity=str(payload.get("severity", "ERROR")),
            details=dict(details) if details is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CadRuntimeEvidenceError(
            "RUNTIME_DIAGNOSTIC_INVALID",
            "runtime diagnostic payload is invalid",
            stage="EVIDENCE",
        ) from exc


class CadRuntimeEvidenceError(CadAdapterError):
    """Fail-closed runtime/readiness error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if not code:
            raise ValueError("runtime error code must not be empty")
        if not stage:
            raise ValueError("runtime error stage must not be empty")
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.details = dict(details or {})

    def to_diagnostic(self) -> RuntimeDiagnostic:
        return RuntimeDiagnostic(
            code=self.code,
            stage=self.stage,
            message=str(self),
            severity="ERROR",
            details=self.details,
        )


def require_host_ready(report: HostReadinessReport) -> None:
    if report.status is HostReadinessStatus.READY:
        return

    blocking = next(
        (
            check
            for check in report.checks
            if check.required and check.status is ReadinessCheckStatus.FAIL
        ),
        None,
    )
    if blocking is None:
        blocking = next(
            (
                check
                for check in report.checks
                if check.required and check.status is ReadinessCheckStatus.UNVERIFIED
            ),
            None,
        )

    if blocking is None:
        raise CadRuntimeEvidenceError(
            "HOST_NOT_READY",
            f"host readiness is {report.status.value}",
            stage="HOST_PREFLIGHT",
        )

    raise CadRuntimeEvidenceError(
        blocking.code,
        blocking.message,
        stage="HOST_PREFLIGHT",
        details={
            "check_status": blocking.status.value,
            **dict(blocking.details or {}),
        },
    )


def _valid_native_artifacts(artifacts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact.get("kind") != _NATIVE_SOLIDWORKS_KIND:
            continue
        artifact_id = artifact.get("artifact_id")
        uri = artifact.get("uri")
        sha256 = artifact.get("sha256")
        if (
            isinstance(artifact_id, str)
            and artifact_id
            and isinstance(uri, str)
            and uri
            and isinstance(sha256, str)
            and _SHA256_RE.fullmatch(sha256)
        ):
            valid.append(dict(artifact))
    return valid


def _validate_execution_identity(
    *,
    execution: Any,
    sketch_package_id: str,
    adapter_name: str,
) -> None:
    mapped_id = execution.mapped_sketch_package.sketch_package_id
    if mapped_id != sketch_package_id:
        raise CadRuntimeEvidenceError(
            "SKETCH_PACKAGE_ID_MISMATCH",
            f"execution sketch_package_id={mapped_id!r} does not match {sketch_package_id!r}",
            stage="EVIDENCE",
        )

    if execution.adapter_result.adapter_name != adapter_name:
        raise CadRuntimeEvidenceError(
            "ADAPTER_IDENTITY_MISMATCH",
            "runtime evidence adapter identity does not match transfer result",
            stage="EVIDENCE",
            details={
                "expected": adapter_name,
                "actual": execution.adapter_result.adapter_name,
            },
        )

    cad_package = execution.cad_package
    report = execution.cad_verification_report
    if cad_package.get("sketch_package_id") != sketch_package_id:
        raise CadRuntimeEvidenceError(
            "CAD_PACKAGE_SKETCH_ID_MISMATCH",
            "CADPackage points to a different SketchPackage",
            stage="EVIDENCE",
        )
    if report.get("sketch_package_id") != sketch_package_id:
        raise CadRuntimeEvidenceError(
            "VERIFICATION_SKETCH_ID_MISMATCH",
            "CADVerificationReport points to a different SketchPackage",
            stage="EVIDENCE",
        )
    if report.get("cad_package_id") != cad_package.get("cad_package_id"):
        raise CadRuntimeEvidenceError(
            "CAD_PACKAGE_REPORT_ID_MISMATCH",
            "CADVerificationReport points to a different CADPackage",
            stage="EVIDENCE",
        )
    if cad_package.get("adapter") != adapter_name:
        raise CadRuntimeEvidenceError(
            "CAD_PACKAGE_ADAPTER_MISMATCH",
            "CADPackage adapter does not match runtime evidence adapter",
            stage="EVIDENCE",
        )

    cad_artifacts = [dict(item) for item in cad_package.get("artifacts", ())]
    adapter_artifacts = [dict(item) for item in execution.adapter_result.artifacts]
    if cad_artifacts != adapter_artifacts:
        raise CadRuntimeEvidenceError(
            "ARTIFACT_EVIDENCE_MISMATCH",
            "CADPackage artifacts differ from adapter result artifacts",
            stage="EVIDENCE",
        )

    read_back = {
        item.dimension_id: item
        for item in execution.adapter_result.read_back.dimensions
    }
    for item in report.get("items", ()):
        dimension_id = item.get("dimension_id")
        actual = item.get("actual")
        if actual is None:
            continue
        native = read_back.get(dimension_id)
        if native is None:
            raise CadRuntimeEvidenceError(
                "READ_BACK_EVIDENCE_MISSING",
                f"verification item {dimension_id!r} has actual value without read-back evidence",
                stage="EVIDENCE",
            )
        if native.unit != item.get("unit") or native.actual_value != actual:
            raise CadRuntimeEvidenceError(
                "READ_BACK_EVIDENCE_MISMATCH",
                f"read-back evidence differs from verification item {dimension_id!r}",
                stage="EVIDENCE",
                details={
                    "read_back_value": native.actual_value,
                    "read_back_unit": native.unit,
                    "report_value": actual,
                    "report_unit": item.get("unit"),
                },
            )


def build_runtime_evidence(
    *,
    sketch_package_id: str,
    adapter_name: str,
    real_host_executed: bool,
    execution: Any | None = None,
    host_readiness: HostReadinessReport | None = None,
    solidworks_version: str | None = None,
    diagnostics: Sequence[RuntimeDiagnostic] = (),
) -> dict[str, Any]:
    """Build slice-local runtime evidence without changing canonical CAD contracts.

    Numerical verification alone is insufficient for real-host VERIFIED. A
    VERIFIED runtime record requires an explicitly executed real host, READY
    host-readiness evidence, a SOLIDWORKS version, a canonical VERIFIED report,
    and at least one native SOLIDWORKS artifact with a SHA-256 digest.
    """

    if not sketch_package_id:
        raise ValueError("sketch_package_id must not be empty")
    if not adapter_name:
        raise ValueError("adapter_name must not be empty")

    if execution is not None:
        _validate_execution_identity(
            execution=execution,
            sketch_package_id=sketch_package_id,
            adapter_name=adapter_name,
        )

    collected = list(diagnostics)
    artifacts: list[dict[str, Any]] = []
    read_back: list[dict[str, Any]] = []
    verification_report: dict[str, Any] | None = None
    cad_package_id: str | None = None

    if execution is not None:
        artifacts = [dict(item) for item in execution.cad_package.get("artifacts", ())]
        cad_package_id = execution.cad_package.get("cad_package_id")
        read_back = [
            {
                "dimension_id": item.dimension_id,
                "actual_value": item.actual_value,
                "unit": item.unit,
            }
            for item in sorted(
                execution.adapter_result.read_back.dimensions,
                key=lambda item: item.dimension_id,
            )
        ]
        verification_report = dict(execution.cad_verification_report)

    if not real_host_executed:
        collected.append(
            RuntimeDiagnostic(
                code="REAL_HOST_NOT_EXECUTED",
                stage="HOST_RUNTIME",
                message="no controlled Windows/SOLIDWORKS host execution was recorded",
                severity="WARNING",
            )
        )
        status = RuntimeEvidenceStatus.UNVERIFIED
    else:
        if host_readiness is None:
            collected.append(
                RuntimeDiagnostic(
                    code="HOST_READINESS_EVIDENCE_MISSING",
                    stage="HOST_PREFLIGHT",
                    message="real-host execution lacks host-readiness evidence",
                )
            )
        elif host_readiness.adapter_name != adapter_name:
            collected.append(
                RuntimeDiagnostic(
                    code="HOST_READINESS_ADAPTER_MISMATCH",
                    stage="HOST_PREFLIGHT",
                    message="host-readiness adapter identity does not match runtime adapter",
                    details={
                        "expected": adapter_name,
                        "actual": host_readiness.adapter_name,
                    },
                )
            )
        elif host_readiness.status is not HostReadinessStatus.READY:
            collected.append(
                RuntimeDiagnostic(
                    code="HOST_NOT_READY",
                    stage="HOST_PREFLIGHT",
                    message=f"host readiness is {host_readiness.status.value}",
                )
            )

        if not solidworks_version:
            collected.append(
                RuntimeDiagnostic(
                    code="SOLIDWORKS_VERSION_MISSING",
                    stage="HOST_RUNTIME",
                    message="real-host execution did not record the SOLIDWORKS version",
                )
            )

        if execution is None:
            collected.append(
                RuntimeDiagnostic(
                    code="CAD_TRANSFER_EXECUTION_MISSING",
                    stage="TRANSFER",
                    message="real-host execution did not produce a CAD transfer execution record",
                )
            )
        elif not _valid_native_artifacts(artifacts):
            collected.append(
                RuntimeDiagnostic(
                    code="NATIVE_ARTIFACT_EVIDENCE_MISSING",
                    stage="ARTIFACT",
                    message="no SOLIDWORKS_PART artifact with identity, URI and SHA-256 was recorded",
                )
            )

        has_error = any(item.severity == "ERROR" for item in collected)
        verification_status = (
            verification_report.get("overall_status")
            if verification_report is not None
            else None
        )
        if has_error or verification_status == "FAILED":
            status = RuntimeEvidenceStatus.FAILED
        elif verification_status == "VERIFIED":
            status = RuntimeEvidenceStatus.VERIFIED
        else:
            status = RuntimeEvidenceStatus.UNVERIFIED

    return {
        "schema_version": RUNTIME_EVIDENCE_SCHEMA,
        "status": status.value,
        "adapter_name": adapter_name,
        "real_host_executed": real_host_executed,
        "solidworks_version": solidworks_version,
        "sketch_package_id": sketch_package_id,
        "cad_package_id": cad_package_id,
        "host_readiness": host_readiness.to_dict() if host_readiness is not None else None,
        "artifacts": artifacts,
        "read_back_dimensions": read_back,
        "verification_report": verification_report,
        "diagnostics": [item.to_dict() for item in collected],
    }
