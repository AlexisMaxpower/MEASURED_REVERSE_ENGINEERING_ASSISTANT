from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .pipeline import CadTransferExecution, execute_cad_transfer_v1
from .runtime_evidence import (
    CadRuntimeEvidenceError,
    HostReadinessReport,
    RuntimeDiagnostic,
    build_runtime_evidence,
    parse_host_readiness_report,
    parse_runtime_diagnostic,
    require_host_ready,
)
from .vendor import (
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
)

SOLIDWORKS_RUNTIME_INPUTS_SCHEMA = "mrea.solidworks-runtime-inputs.v1"
SOLIDWORKS_RUNTIME_INPUTS_PRODUCER = "SIDE_CHAT_4B"
SOLIDWORKS_RUNTIME_ADAPTER_NAME = "SOLIDWORKS_2026"

_REQUIRED_READINESS_CODES = frozenset(
    {
        "OS_WINDOWS_11_X64",
        "PROCESS_X64",
        "DOTNET_FRAMEWORK_48",
        "AGENT_EXECUTABLE_AVAILABLE",
        "SOLIDWORKS_COM_REGISTERED",
        "SOLIDWORKS_VERSION_2026",
        "SOLIDWORKS_INTEROP_AVAILABLE",
        "OUTPUT_PATH_WRITABLE",
        "PART_TEMPLATE_AVAILABLE",
    }
)
_KNOWN_AGENT_EXIT_CODES = frozenset({0, 20, 30, 40, 50, 70})


@dataclass(frozen=True, slots=True)
class SolidWorksRuntimeInputs:
    """Validated Side Chat 4B facts; not a shared/canonical contract."""

    host_readiness: HostReadinessReport
    agent_exit_code: int
    real_host_executed: bool
    solidworks_version: str | None
    sketch_package_id: str
    adapter_result: CadAdapterResult | None
    diagnostics: tuple[RuntimeDiagnostic, ...]
    canonical_verification_report: Mapping[str, Any] | None


class _RecordedSolidWorksAdapter:
    adapter_name = SOLIDWORKS_RUNTIME_ADAPTER_NAME

    def __init__(self, result: CadAdapterResult) -> None:
        self._result = result

    def transfer(self, package: Any) -> CadAdapterResult:
        return self._result


def _error(
    code: str,
    message: str,
    *,
    stage: str = "EVIDENCE",
    details: Mapping[str, Any] | None = None,
) -> CadRuntimeEvidenceError:
    return CadRuntimeEvidenceError(code, message, stage=stage, details=details)


def _parse_adapter_result(payload: Mapping[str, Any]) -> CadAdapterResult:
    raw_bindings = payload.get("bindings")
    raw_dimensions = payload.get("read_back_dimensions")
    raw_conflicts = payload.get("constraint_conflicts", ())
    raw_artifacts = payload.get("artifacts", ())

    if not isinstance(raw_bindings, list):
        raise _error(
            "SOLIDWORKS_RUNTIME_BINDINGS_INVALID",
            "runtime inputs require a bindings array",
        )
    if not isinstance(raw_dimensions, list):
        raise _error(
            "SOLIDWORKS_RUNTIME_READ_BACK_INVALID",
            "runtime inputs require a read_back_dimensions array",
        )
    if not isinstance(raw_conflicts, list):
        raise _error(
            "SOLIDWORKS_RUNTIME_CONFLICTS_INVALID",
            "constraint_conflicts must be an array",
        )
    if not isinstance(raw_artifacts, list):
        raise _error(
            "SOLIDWORKS_RUNTIME_ARTIFACTS_INVALID",
            "artifacts must be an array",
        )

    try:
        bindings_list: list[CadDimensionBinding] = []
        for item in raw_bindings:
            if not isinstance(item, Mapping):
                raise TypeError("binding must be an object")
            dimension_id = item["dimension_id"]
            measurement_id = item.get("measurement_id")
            vendor_ref = item["vendor_dimension_ref"]
            if not isinstance(dimension_id, str):
                raise TypeError("binding dimension_id must be a string")
            if measurement_id is not None and not isinstance(measurement_id, str):
                raise TypeError("binding measurement_id must be null or string")
            if not isinstance(vendor_ref, str):
                raise TypeError("vendor_dimension_ref must be a string")
            bindings_list.append(
                CadDimensionBinding(
                    dimension_id=dimension_id,
                    measurement_id=measurement_id,
                    vendor_dimension_ref=vendor_ref,
                )
            )
        bindings = tuple(bindings_list)

        dimensions_list: list[CadReadBackDimension] = []
        for item in raw_dimensions:
            if not isinstance(item, Mapping):
                raise TypeError("read-back dimension must be an object")
            dimension_id = item["dimension_id"]
            actual_value = item["actual_value"]
            unit = item["unit"]
            if not isinstance(dimension_id, str):
                raise TypeError("read-back dimension_id must be a string")
            if (
                not isinstance(actual_value, (int, float))
                or isinstance(actual_value, bool)
            ):
                raise TypeError("read-back actual_value must be numeric")
            if not isinstance(unit, str):
                raise TypeError("read-back unit must be a string")
            dimensions_list.append(
                CadReadBackDimension(
                    dimension_id=dimension_id,
                    actual_value=float(actual_value),
                    unit=unit,
                )
            )
        dimensions = tuple(dimensions_list)

        conflicts = frozenset(str(item) for item in raw_conflicts)
        artifacts = tuple(
            dict(item) for item in raw_artifacts if isinstance(item, Mapping)
        )
        if len(artifacts) != len(raw_artifacts):
            raise TypeError("artifact must be an object")

        return CadAdapterResult(
            adapter_name=SOLIDWORKS_RUNTIME_ADAPTER_NAME,
            bindings=bindings,
            read_back=CadReadBack(
                dimensions=dimensions,
                constraint_conflicts=conflicts,
            ),
            artifacts=artifacts,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _error(
            "SOLIDWORKS_RUNTIME_VENDOR_DATA_INVALID",
            "runtime inputs contain invalid vendor-neutral CAD data",
        ) from exc


def parse_solidworks_runtime_inputs_v1(
    payload: Mapping[str, Any],
) -> SolidWorksRuntimeInputs:
    """Parse Side Chat 4B's slice-local runtime-input bundle fail-closed."""

    if payload.get("schema_version") != SOLIDWORKS_RUNTIME_INPUTS_SCHEMA:
        raise _error(
            "SOLIDWORKS_RUNTIME_INPUTS_SCHEMA_MISMATCH",
            f"expected {SOLIDWORKS_RUNTIME_INPUTS_SCHEMA!r}, "
            f"got {payload.get('schema_version')!r}",
        )
    if payload.get("producer") != SOLIDWORKS_RUNTIME_INPUTS_PRODUCER:
        raise _error(
            "SOLIDWORKS_RUNTIME_INPUTS_PRODUCER_MISMATCH",
            "runtime inputs must come from SIDE_CHAT_4B",
        )
    if "status" in payload:
        raise _error(
            "SOLIDWORKS_RUNTIME_FINAL_STATUS_FORBIDDEN",
            "side runtime inputs must not claim final runtime status",
        )
    if payload.get("adapter_name") != SOLIDWORKS_RUNTIME_ADAPTER_NAME:
        raise _error(
            "SOLIDWORKS_RUNTIME_ADAPTER_MISMATCH",
            "runtime inputs adapter_name must be SOLIDWORKS_2026",
        )

    raw_readiness = payload.get("host_readiness")
    if not isinstance(raw_readiness, Mapping):
        raise _error(
            "SOLIDWORKS_RUNTIME_READINESS_MISSING",
            "runtime inputs require host_readiness",
            stage="HOST_PREFLIGHT",
        )
    readiness = parse_host_readiness_report(raw_readiness)
    if readiness.adapter_name != SOLIDWORKS_RUNTIME_ADAPTER_NAME:
        raise _error(
            "SOLIDWORKS_RUNTIME_READINESS_ADAPTER_MISMATCH",
            "host_readiness adapter_name must be SOLIDWORKS_2026",
            stage="HOST_PREFLIGHT",
        )

    checks_by_code = {check.code: check for check in readiness.checks}
    missing = sorted(_REQUIRED_READINESS_CODES - set(checks_by_code))
    if missing:
        raise _error(
            "SOLIDWORKS_RUNTIME_READINESS_CODES_MISSING",
            "host readiness is missing mandatory Side Chat 4B checks",
            stage="HOST_PREFLIGHT",
            details={"missing_codes": missing},
        )
    optionalized = sorted(
        code for code in _REQUIRED_READINESS_CODES if not checks_by_code[code].required
    )
    if optionalized:
        raise _error(
            "SOLIDWORKS_RUNTIME_READINESS_CODE_NOT_REQUIRED",
            "mandatory host-readiness checks cannot be marked optional",
            stage="HOST_PREFLIGHT",
            details={"codes": optionalized},
        )

    agent_exit_code = payload.get("agent_exit_code")
    if not isinstance(agent_exit_code, int) or isinstance(agent_exit_code, bool):
        raise _error(
            "SOLIDWORKS_RUNTIME_EXIT_CODE_INVALID",
            "agent_exit_code must be an integer",
            stage="HOST_RUNTIME",
        )
    if agent_exit_code not in _KNOWN_AGENT_EXIT_CODES:
        raise _error(
            "SOLIDWORKS_RUNTIME_EXIT_CODE_UNKNOWN",
            f"unsupported agent_exit_code: {agent_exit_code}",
            stage="HOST_RUNTIME",
        )

    real_host_executed = payload.get("real_host_executed")
    if not isinstance(real_host_executed, bool):
        raise _error(
            "SOLIDWORKS_RUNTIME_HOST_FLAG_INVALID",
            "real_host_executed must be boolean",
            stage="HOST_RUNTIME",
        )

    solidworks_version = payload.get("solidworks_version")
    if solidworks_version is not None and (
        not isinstance(solidworks_version, str) or not solidworks_version.strip()
    ):
        raise _error(
            "SOLIDWORKS_RUNTIME_VERSION_INVALID",
            "solidworks_version must be null or a non-empty string",
            stage="HOST_RUNTIME",
        )

    sketch_package_id = payload.get("sketch_package_id")
    if not isinstance(sketch_package_id, str) or not sketch_package_id:
        raise _error(
            "SOLIDWORKS_RUNTIME_SKETCH_ID_INVALID",
            "runtime inputs require a non-empty sketch_package_id",
        )

    raw_diagnostics = payload.get("diagnostics", ())
    if not isinstance(raw_diagnostics, list):
        raise _error(
            "SOLIDWORKS_RUNTIME_DIAGNOSTICS_INVALID",
            "diagnostics must be an array",
        )
    diagnostics: list[RuntimeDiagnostic] = []
    for item in raw_diagnostics:
        if not isinstance(item, Mapping):
            raise _error(
                "SOLIDWORKS_RUNTIME_DIAGNOSTICS_INVALID",
                "each diagnostic must be an object",
            )
        diagnostics.append(parse_runtime_diagnostic(item))

    raw_report = payload.get("canonical_verification_report")
    if raw_report is not None and not isinstance(raw_report, Mapping):
        raise _error(
            "SOLIDWORKS_RUNTIME_CANONICAL_REPORT_INVALID",
            "canonical_verification_report must be null or an object",
        )

    adapter_result = _parse_adapter_result(payload) if agent_exit_code == 0 else None

    return SolidWorksRuntimeInputs(
        host_readiness=readiness,
        agent_exit_code=agent_exit_code,
        real_host_executed=real_host_executed,
        solidworks_version=solidworks_version,
        sketch_package_id=sketch_package_id,
        adapter_result=adapter_result,
        diagnostics=tuple(diagnostics),
        canonical_verification_report=(
            dict(raw_report) if raw_report is not None else None
        ),
    )


def _replay_successful_transfer(
    *,
    sketch_package: Mapping[str, Any],
    inputs: SolidWorksRuntimeInputs,
) -> CadTransferExecution:
    if inputs.adapter_result is None:
        raise _error(
            "SOLIDWORKS_RUNTIME_ADAPTER_RESULT_MISSING",
            "successful agent inputs require vendor-neutral CAD data",
        )
    if inputs.canonical_verification_report is None:
        raise _error(
            "SOLIDWORKS_RUNTIME_CANONICAL_REPORT_MISSING",
            "successful agent inputs require canonical_verification_report",
        )

    report_id = inputs.canonical_verification_report.get("report_id")
    cad_package_id = inputs.canonical_verification_report.get("cad_package_id")
    if not isinstance(report_id, str) or not report_id:
        raise _error(
            "SOLIDWORKS_RUNTIME_REPORT_ID_INVALID",
            "canonical_verification_report requires report_id",
        )
    if not isinstance(cad_package_id, str) or not cad_package_id:
        raise _error(
            "SOLIDWORKS_RUNTIME_CAD_PACKAGE_ID_INVALID",
            "canonical_verification_report requires cad_package_id",
        )

    execution = execute_cad_transfer_v1(
        sketch_package=sketch_package,
        adapter=_RecordedSolidWorksAdapter(inputs.adapter_result),
        cad_package_id=cad_package_id,
        report_id=report_id,
    )

    if execution.cad_verification_report != dict(
        inputs.canonical_verification_report
    ):
        raise _error(
            "SOLIDWORKS_CANONICAL_REPORT_MISMATCH",
            "side-supplied canonical verification report does not match Primary replay",
        )
    return execution


def build_solidworks_runtime_evidence_from_inputs_v1(
    *,
    sketch_package: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert side-local facts into Primary-owned runtime evidence.

    Canonical verification is replayed from normalized bindings/read-back. Side
    Chat 4B supplies facts, while Primary Chat 4 remains the sole owner of the
    final VERIFIED / FAILED / UNVERIFIED runtime decision.
    """

    inputs = parse_solidworks_runtime_inputs_v1(runtime_inputs)

    source_sketch_id = sketch_package.get("sketch_package_id")
    if source_sketch_id != inputs.sketch_package_id:
        raise _error(
            "SOLIDWORKS_RUNTIME_SKETCH_ID_MISMATCH",
            "runtime inputs refer to a different SketchPackage",
            details={
                "expected": source_sketch_id,
                "actual": inputs.sketch_package_id,
            },
        )

    diagnostics: list[RuntimeDiagnostic] = list(inputs.diagnostics)
    execution: CadTransferExecution | None = None

    if inputs.agent_exit_code == 0:
        require_host_ready(inputs.host_readiness)
        if inputs.real_host_executed is not True:
            raise _error(
                "SOLIDWORKS_RUNTIME_REAL_HOST_REQUIRED",
                "successful agent inputs must assert real_host_executed=true",
                stage="HOST_RUNTIME",
            )
        if not inputs.solidworks_version:
            raise _error(
                "SOLIDWORKS_RUNTIME_VERSION_MISSING",
                "successful agent inputs require solidworks_version",
                stage="HOST_RUNTIME",
            )
        execution = _replay_successful_transfer(
            sketch_package=sketch_package,
            inputs=inputs,
        )
    else:
        diagnostics.append(
            RuntimeDiagnostic(
                code="SOLIDWORKS_AGENT_EXIT_NONZERO",
                stage="HOST_RUNTIME",
                message=(
                    "SOLIDWORKS CAD Agent exited with code "
                    f"{inputs.agent_exit_code}"
                ),
                severity="ERROR",
                details={"agent_exit_code": inputs.agent_exit_code},
            )
        )

    return build_runtime_evidence(
        sketch_package_id=inputs.sketch_package_id,
        adapter_name=SOLIDWORKS_RUNTIME_ADAPTER_NAME,
        real_host_executed=inputs.real_host_executed,
        execution=execution,
        host_readiness=inputs.host_readiness,
        solidworks_version=inputs.solidworks_version,
        diagnostics=tuple(diagnostics),
    )
