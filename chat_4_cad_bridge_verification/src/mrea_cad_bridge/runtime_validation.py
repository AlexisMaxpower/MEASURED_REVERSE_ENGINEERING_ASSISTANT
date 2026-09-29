from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .pipeline import CadTransferExecution, execute_cad_transfer_v1
from .runtime_evidence import (
    CadRuntimeEvidenceError,
    HostReadinessReport,
    ReadinessCheckStatus,
    RuntimeDiagnostic,
    build_runtime_evidence,
    require_host_ready,
)
from .solidworks_runtime_inputs import (
    SolidWorksRuntimeInputs,
    build_solidworks_runtime_evidence_from_inputs_v1,
    parse_solidworks_runtime_inputs_v1,
)
from .vendor import CadAdapter, CadAdapterResult

SOLIDWORKS_2026_REVISION_MAJOR = 34


@dataclass(frozen=True, slots=True)
class CadRuntimeValidationExecution:
    """One deterministic transfer + runtime-evidence result."""

    transfer_execution: CadTransferExecution
    runtime_evidence: dict[str, Any]

    @property
    def verification_status(self) -> str:
        return str(self.transfer_execution.cad_verification_report["overall_status"])

    @property
    def runtime_status(self) -> str:
        return str(self.runtime_evidence["status"])


@dataclass(frozen=True, slots=True)
class SolidWorksRuntimeValidationExecution:
    """Primary evaluation of one Side-4B runtime-input bundle.

    Failed/non-zero worker runs legitimately have no canonical transfer execution,
    but still produce fail-closed runtime evidence.
    """

    runtime_inputs: SolidWorksRuntimeInputs
    transfer_execution: CadTransferExecution | None
    runtime_evidence: dict[str, Any]

    @property
    def verification_status(self) -> str | None:
        if self.transfer_execution is None:
            return None
        return str(self.transfer_execution.cad_verification_report["overall_status"])

    @property
    def runtime_status(self) -> str:
        return str(self.runtime_evidence["status"])


class _RecordedRuntimeAdapter:
    def __init__(self, result: CadAdapterResult) -> None:
        self.adapter_name = result.adapter_name
        self._result = result

    def transfer(self, package: Any) -> CadAdapterResult:
        return self._result


def _runtime_error(
    code: str,
    message: str,
    *,
    stage: str = "HOST_RUNTIME",
    details: Mapping[str, Any] | None = None,
) -> CadRuntimeEvidenceError:
    return CadRuntimeEvidenceError(code, message, stage=stage, details=details)


def _require_real_host_preconditions(
    *,
    adapter: CadAdapter,
    host_readiness: HostReadinessReport | None,
    solidworks_version: str | None,
) -> None:
    """Fail closed before any vendor transfer is invoked."""

    if host_readiness is None:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_EVIDENCE_MISSING",
            "real-host CAD transfer requires host-readiness evidence before execution",
            stage="HOST_PREFLIGHT",
        )

    if host_readiness.adapter_name != adapter.adapter_name:
        raise CadRuntimeEvidenceError(
            "HOST_READINESS_ADAPTER_MISMATCH",
            "host-readiness adapter identity does not match the selected CAD adapter",
            stage="HOST_PREFLIGHT",
            details={
                "expected": adapter.adapter_name,
                "actual": host_readiness.adapter_name,
            },
        )

    require_host_ready(host_readiness)

    if not isinstance(solidworks_version, str) or not solidworks_version.strip():
        raise CadRuntimeEvidenceError(
            "SOLIDWORKS_VERSION_MISSING",
            "real-host CAD transfer requires a detected SOLIDWORKS version before execution",
            stage="HOST_PREFLIGHT",
        )


def execute_cad_runtime_validation_v1(
    *,
    sketch_package: Mapping[str, Any],
    adapter: CadAdapter,
    cad_package_id: str,
    report_id: str,
    real_host_executed: bool,
    host_readiness: HostReadinessReport | None = None,
    solidworks_version: str | None = None,
    diagnostics: Sequence[RuntimeDiagnostic] = (),
) -> CadRuntimeValidationExecution:
    """Run canonical transfer and build fail-closed runtime evidence.

    For a real-host execution, readiness/identity/version checks happen before
    ``adapter.transfer``. Generic/test-double runs remain allowed but their
    runtime evidence stays UNVERIFIED.
    """

    if real_host_executed:
        _require_real_host_preconditions(
            adapter=adapter,
            host_readiness=host_readiness,
            solidworks_version=solidworks_version,
        )

    transfer = execute_cad_transfer_v1(
        sketch_package=sketch_package,
        adapter=adapter,
        cad_package_id=cad_package_id,
        report_id=report_id,
    )

    evidence = build_runtime_evidence(
        sketch_package_id=transfer.mapped_sketch_package.sketch_package_id,
        adapter_name=adapter.adapter_name,
        real_host_executed=real_host_executed,
        execution=transfer,
        host_readiness=host_readiness,
        solidworks_version=solidworks_version,
        diagnostics=diagnostics,
    )

    return CadRuntimeValidationExecution(
        transfer_execution=transfer,
        runtime_evidence=evidence,
    )


def _parse_revision_major(version: str) -> int:
    try:
        major_text = version.strip().split(".", 1)[0]
        major = int(major_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_UNPARSEABLE",
            "solidworks_version must start with a numeric RevisionNumber major",
            details={"solidworks_version": version},
        ) from exc
    if major <= 0:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_UNPARSEABLE",
            "solidworks_version must contain a positive RevisionNumber major",
            details={"solidworks_version": version},
        )
    return major


def _validate_solidworks_cross_evidence(
    *,
    raw_inputs: Mapping[str, Any],
    parsed: SolidWorksRuntimeInputs,
) -> None:
    """Cross-check independent Side-4B facts before final Primary evaluation."""

    raw_conflicts = raw_inputs.get("constraint_conflicts", ())
    if not isinstance(raw_conflicts, list) or any(
        not isinstance(item, str) or not item for item in raw_conflicts
    ):
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_CONFLICTS_INVALID",
            "constraint_conflicts must contain only non-empty canonical dimension IDs",
            stage="EVIDENCE",
        )

    if parsed.solidworks_version is None:
        if parsed.real_host_executed and parsed.agent_exit_code == 0:
            raise _runtime_error(
                "SOLIDWORKS_RUNTIME_VERSION_MISSING",
                "successful real-host execution requires solidworks_version",
            )
        return

    major = _parse_revision_major(parsed.solidworks_version)
    if major != SOLIDWORKS_2026_REVISION_MAJOR:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_MAJOR_MISMATCH",
            "worker-reported SOLIDWORKS RevisionNumber major is not the 2026 baseline",
            details={
                "expected_revision_major": SOLIDWORKS_2026_REVISION_MAJOR,
                "actual_revision_major": major,
                "solidworks_version": parsed.solidworks_version,
            },
        )

    version_check = next(
        (
            check
            for check in parsed.host_readiness.checks
            if check.code == "SOLIDWORKS_VERSION_2026"
        ),
        None,
    )
    if version_check is None:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_CHECK_MISSING",
            "host readiness must include SOLIDWORKS_VERSION_2026",
            stage="HOST_PREFLIGHT",
        )
    if parsed.agent_exit_code == 0 and version_check.status is not ReadinessCheckStatus.PASS:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_CHECK_NOT_PASS",
            "successful worker execution requires a PASS SOLIDWORKS_VERSION_2026 readiness check",
            stage="HOST_PREFLIGHT",
        )

    details = version_check.details or {}
    readiness_revision = details.get("revision_number")
    if readiness_revision is not None and readiness_revision != parsed.solidworks_version:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_MISMATCH",
            "host-readiness revision_number disagrees with worker solidworks_version",
            details={
                "host_readiness_revision": readiness_revision,
                "worker_revision": parsed.solidworks_version,
            },
        )

    readiness_major = details.get("revision_major")
    if readiness_major is not None:
        try:
            normalized_major = int(readiness_major)
        except (TypeError, ValueError) as exc:
            raise _runtime_error(
                "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_INVALID",
                "host-readiness revision_major is not an integer",
                details={"revision_major": readiness_major},
            ) from exc
        if normalized_major != major:
            raise _runtime_error(
                "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_MISMATCH",
                "host-readiness revision_major disagrees with worker solidworks_version",
                details={
                    "host_readiness_major": normalized_major,
                    "worker_major": major,
                },
            )

    expected_major = details.get("expected_revision_major")
    if expected_major is not None:
        try:
            normalized_expected = int(expected_major)
        except (TypeError, ValueError) as exc:
            raise _runtime_error(
                "SOLIDWORKS_RUNTIME_VERSION_EVIDENCE_INVALID",
                "host-readiness expected_revision_major is not an integer",
                details={"expected_revision_major": expected_major},
            ) from exc
        if normalized_expected != SOLIDWORKS_2026_REVISION_MAJOR:
            raise _runtime_error(
                "SOLIDWORKS_RUNTIME_VERSION_BASELINE_MISMATCH",
                "host-readiness evidence was produced for a different SOLIDWORKS major",
                details={
                    "expected_revision_major": SOLIDWORKS_2026_REVISION_MAJOR,
                    "evidence_expected_revision_major": normalized_expected,
                },
            )


def evaluate_solidworks_runtime_inputs_v1(
    *,
    sketch_package: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> SolidWorksRuntimeValidationExecution:
    """Evaluate Side-4B facts through the final Primary runtime path.

    This is the preferred Pass-5 entry point for recorded SOLIDWORKS host facts.
    The side-local bundle is parsed fail-closed, cross-evidence is checked, the
    existing Pass-3 Primary bridge produces final runtime evidence, and a
    successful transfer is replayed through ``execute_cad_runtime_validation_v1``
    so both runtime paths must agree exactly.
    """

    parsed = parse_solidworks_runtime_inputs_v1(runtime_inputs)
    _validate_solidworks_cross_evidence(raw_inputs=runtime_inputs, parsed=parsed)

    bridge_evidence = build_solidworks_runtime_evidence_from_inputs_v1(
        sketch_package=sketch_package,
        runtime_inputs=runtime_inputs,
    )

    if parsed.agent_exit_code != 0:
        return SolidWorksRuntimeValidationExecution(
            runtime_inputs=parsed,
            transfer_execution=None,
            runtime_evidence=bridge_evidence,
        )

    if parsed.adapter_result is None or parsed.canonical_verification_report is None:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_SUCCESS_DATA_MISSING",
            "successful Side-4B inputs require adapter result and canonical verification report",
            stage="EVIDENCE",
        )

    cad_package_id = parsed.canonical_verification_report.get("cad_package_id")
    report_id = parsed.canonical_verification_report.get("report_id")
    if not isinstance(cad_package_id, str) or not cad_package_id:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_CAD_PACKAGE_ID_INVALID",
            "canonical verification report requires cad_package_id",
            stage="EVIDENCE",
        )
    if not isinstance(report_id, str) or not report_id:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_REPORT_ID_INVALID",
            "canonical verification report requires report_id",
            stage="EVIDENCE",
        )

    direct = execute_cad_runtime_validation_v1(
        sketch_package=sketch_package,
        adapter=_RecordedRuntimeAdapter(parsed.adapter_result),
        cad_package_id=cad_package_id,
        report_id=report_id,
        real_host_executed=parsed.real_host_executed,
        host_readiness=parsed.host_readiness,
        solidworks_version=parsed.solidworks_version,
        diagnostics=parsed.diagnostics,
    )

    if direct.runtime_evidence != bridge_evidence:
        raise _runtime_error(
            "SOLIDWORKS_RUNTIME_PATH_DIVERGENCE",
            "direct runtime-validation evidence disagrees with the Pass-3 Side-input bridge",
            stage="EVIDENCE",
        )

    return SolidWorksRuntimeValidationExecution(
        runtime_inputs=parsed,
        transfer_execution=direct.transfer_execution,
        runtime_evidence=bridge_evidence,
    )
