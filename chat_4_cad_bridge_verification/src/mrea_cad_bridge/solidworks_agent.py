from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping, Protocol

from .contracts import MappedSketchPackage
from .solidworks_capabilities import evaluate_solidworks_constraint_support_v1
from .solidworks_constraint_handshake import SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256
from .solidworks_dimension_capabilities import evaluate_solidworks_dimension_support_v1
from .solidworks_entity_capabilities import evaluate_solidworks_entity_support_v1
from .solidworks_worker_handshake import (
    SOLIDWORKS_WORKER_CAPABILITIES_SHA256,
    build_solidworks_worker_capability_projection_v1,
)
from .vendor import (
    CadAdapterError,
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
)

SOLIDWORKS_AGENT_PROTOCOL = "mrea.solidworks-agent.v1"
SOLIDWORKS_ADAPTER_NAME = "SOLIDWORKS_2026"
_WORKER_CAPABILITY_PROJECTION = build_solidworks_worker_capability_projection_v1()
_SUPPORTED_ENTITY_TYPES = frozenset(
    _WORKER_CAPABILITY_PROJECTION["geometry_entities"]["supported"]
)
_SUPPORTED_DIMENSION_TYPES = frozenset(
    _WORKER_CAPABILITY_PROJECTION["verified_dimensions"]["supported"]
)


@dataclass(frozen=True, slots=True)
class SolidWorksAgentConfig:
    executable_path: Path
    output_directory: Path
    part_template_path: Path | None = None
    attach_to_running: bool = True
    allow_launch: bool = True
    timeout_seconds: float = 180.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


class SolidWorksAgentRunner(Protocol):
    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class SubprocessSolidWorksAgentRunner:
    """Runs the .NET Framework SOLIDWORKS CAD Agent as a one-shot worker process."""

    def __init__(self, config: SolidWorksAgentConfig) -> None:
        self._config = config

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        executable = self._config.executable_path
        if not executable.is_file():
            raise CadAdapterError(f"SOLIDWORKS CAD Agent executable not found: {executable}")

        self._config.output_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mrea-sw-agent-") as temp_dir:
            temp_root = Path(temp_dir)
            request_path = temp_root / "request.json"
            response_path = temp_root / "response.json"
            request_path.write_text(
                json.dumps(request, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            try:
                completed = subprocess.run(
                    [
                        str(executable),
                        "--request",
                        str(request_path),
                        "--response",
                        str(response_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self._config.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise CadAdapterError(
                    "SOLIDWORKS CAD Agent timed out after "
                    f"{self._config.timeout_seconds:g} seconds"
                ) from exc

            if not response_path.is_file():
                stderr = completed.stderr.strip()
                stdout = completed.stdout.strip()
                detail = stderr or stdout or "no process output"
                raise CadAdapterError(
                    "SOLIDWORKS CAD Agent did not produce a response "
                    f"(exit={completed.returncode}): {detail}"
                )

            try:
                response = json.loads(response_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CadAdapterError("SOLIDWORKS CAD Agent returned invalid JSON") from exc

            if completed.returncode != 0 and response.get("status") == "OK":
                raise CadAdapterError(
                    "SOLIDWORKS CAD Agent exited non-zero while claiming OK: "
                    f"{completed.returncode}"
                )
            return response


def _verified_dimension_contracts(package: MappedSketchPackage) -> tuple[Mapping[str, Any], ...]:
    expected_ids = {item.dimension_id for item in package.expected_dimensions}
    return tuple(
        item for item in package.dimensions if item.get("dimension_id") in expected_ids
    )


def _validate_entity_support(entity: Mapping[str, Any]) -> None:
    decision = evaluate_solidworks_entity_support_v1(entity)
    if decision.supported:
        return
    raise CadAdapterError(
        "SOLIDWORKS entity preflight failed "
        f"[{decision.code}] {decision.entity_id}: {decision.message}"
    )


def _validate_constraint_support(
    constraint: Mapping[str, Any],
    entities_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    decision = evaluate_solidworks_constraint_support_v1(constraint, entities_by_id)
    if decision.supported:
        return
    raise CadAdapterError(
        "SOLIDWORKS constraint preflight failed "
        f"[{decision.code}] {decision.constraint_id}: {decision.message}"
    )


def _validate_dimension_support(
    dimension: Mapping[str, Any],
    entities_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    decision = evaluate_solidworks_dimension_support_v1(dimension, entities_by_id)
    if decision.supported:
        return
    raise CadAdapterError(
        "SOLIDWORKS dimension preflight failed "
        f"[{decision.code}] {decision.dimension_id}: {decision.message}"
    )


def _preflight(package: MappedSketchPackage) -> None:
    verified_dimensions = _verified_dimension_contracts(package)
    verified_entity_ids = {
        entity_id
        for dimension in verified_dimensions
        for entity_id in dimension.get("entity_ids", ())
    }
    verified_measurement_ids = {
        item.measurement_id
        for item in package.expected_dimensions
        if item.measurement_id is not None
    }

    blocking: list[str] = []
    for unresolved in package.unresolved:
        unresolved_entities = set(unresolved.get("entity_ids") or ())
        unresolved_measurements = set(unresolved.get("measurement_ids") or ())
        if unresolved_entities & verified_entity_ids or unresolved_measurements & verified_measurement_ids:
            blocking.append(str(unresolved.get("unresolved_id", "<unknown>")))
    if blocking:
        raise CadAdapterError(
            "unresolved geometry/measurement affects verified CAD dimensions: "
            f"{sorted(blocking)!r}"
        )

    entities_by_id: dict[str, Mapping[str, Any]] = {}
    for entity in package.entity_contracts:
        _validate_entity_support(entity)
        entity_id = str(entity.get("entity_id"))
        if entity_id in entities_by_id:
            raise CadAdapterError(
                "SOLIDWORKS entity preflight failed "
                f"[ENTITY_ID_DUPLICATE] {entity_id}: duplicate entity_id"
            )
        entities_by_id[entity_id] = entity

    unsupported_dimensions = sorted(
        {
            str(dimension.get("type"))
            for dimension in verified_dimensions
            if dimension.get("type") not in _SUPPORTED_DIMENSION_TYPES
        }
    )
    if unsupported_dimensions:
        raise CadAdapterError(
            "SOLIDWORKS vendor slice does not support verified dimension types: "
            f"{unsupported_dimensions!r}"
        )

    for constraint in package.constraints:
        _validate_constraint_support(constraint, entities_by_id)
    for dimension in verified_dimensions:
        _validate_dimension_support(dimension, entities_by_id)


def build_solidworks_agent_request(
    package: MappedSketchPackage,
    config: SolidWorksAgentConfig,
) -> dict[str, Any]:
    """Build the slice-local process protocol sent to the C# CAD Agent."""

    _preflight(package)
    verified_dimensions = _verified_dimension_contracts(package)

    return {
        "protocol_version": SOLIDWORKS_AGENT_PROTOCOL,
        "adapter_name": SOLIDWORKS_ADAPTER_NAME,
        "worker_capabilities_sha256": SOLIDWORKS_WORKER_CAPABILITIES_SHA256,
        "constraint_capabilities_sha256": SOLIDWORKS_CONSTRAINT_CAPABILITIES_SHA256,
        "sketch_package_id": package.sketch_package_id,
        "output_directory": str(config.output_directory.resolve()),
        "part_template_path": (
            str(config.part_template_path.resolve())
            if config.part_template_path is not None
            else None
        ),
        "attach_to_running": config.attach_to_running,
        "allow_launch": config.allow_launch,
        "entities": [dict(entity) for entity in package.entity_contracts],
        "constraints": [dict(constraint) for constraint in package.constraints],
        "dimensions": [dict(dimension) for dimension in verified_dimensions],
    }


def _parse_constraint_conflicts(
    read_back_raw: Mapping[str, Any],
    *,
    bound_dimension_ids: frozenset[str],
) -> frozenset[str]:
    raw_conflicts = read_back_raw.get("constraint_conflicts", ())
    if not isinstance(raw_conflicts, (list, tuple)):
        raise CadAdapterError(
            "invalid SOLIDWORKS CAD Agent response shape: "
            "read_back.constraint_conflicts must be an array"
        )

    seen: set[str] = set()
    for raw_dimension_id in raw_conflicts:
        if not isinstance(raw_dimension_id, str) or not raw_dimension_id:
            raise CadAdapterError(
                "invalid SOLIDWORKS CAD Agent response shape: "
                "constraint conflict IDs must be non-empty strings"
            )
        if raw_dimension_id in seen:
            raise CadAdapterError(
                "invalid SOLIDWORKS CAD Agent response shape: "
                f"duplicate constraint conflict dimension_id {raw_dimension_id!r}"
            )
        seen.add(raw_dimension_id)

    unknown = seen - bound_dimension_ids
    if unknown:
        raise CadAdapterError(
            "SOLIDWORKS CAD Agent returned constraint conflicts for unbound dimensions: "
            f"{sorted(unknown)!r}"
        )
    return frozenset(seen)


def parse_solidworks_agent_response(response: Mapping[str, Any]) -> CadAdapterResult:
    if response.get("protocol_version") != SOLIDWORKS_AGENT_PROTOCOL:
        raise CadAdapterError(
            "SOLIDWORKS CAD Agent protocol mismatch: "
            f"{response.get('protocol_version')!r}"
        )
    if response.get("status") != "OK":
        error = response.get("error") or {}
        message = error.get("message") if isinstance(error, Mapping) else None
        raise CadAdapterError(
            f"SOLIDWORKS CAD Agent failed: {message or 'unspecified agent error'}"
        )
    if response.get("adapter_name") != SOLIDWORKS_ADAPTER_NAME:
        raise CadAdapterError(
            "SOLIDWORKS CAD Agent adapter identity mismatch: "
            f"{response.get('adapter_name')!r}"
        )

    try:
        bindings = tuple(
            CadDimensionBinding(
                dimension_id=item["dimension_id"],
                measurement_id=item.get("measurement_id"),
                vendor_dimension_ref=item["vendor_dimension_ref"],
            )
            for item in response.get("bindings", ())
        )
        bound_dimension_ids = frozenset(binding.dimension_id for binding in bindings)
        read_back_raw = response["read_back"]
        if not isinstance(read_back_raw, Mapping):
            raise TypeError("read_back must be an object")
        dimensions = tuple(
            CadReadBackDimension(
                dimension_id=item["dimension_id"],
                actual_value=float(item["actual_value"]),
                unit=item["unit"],
            )
            for item in read_back_raw.get("dimensions", ())
        )
        conflicts = _parse_constraint_conflicts(
            read_back_raw,
            bound_dimension_ids=bound_dimension_ids,
        )
        artifacts = tuple(dict(item) for item in response.get("artifacts", ()))
    except CadAdapterError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise CadAdapterError("invalid SOLIDWORKS CAD Agent response shape") from exc

    return CadAdapterResult(
        adapter_name=SOLIDWORKS_ADAPTER_NAME,
        bindings=bindings,
        read_back=CadReadBack(
            dimensions=dimensions,
            constraint_conflicts=conflicts,
        ),
        artifacts=artifacts,
    )


class SolidWorksAgentAdapter:
    """Production vendor adapter boundary for the out-of-process SOLIDWORKS 2026 agent."""

    adapter_name = SOLIDWORKS_ADAPTER_NAME

    def __init__(
        self,
        config: SolidWorksAgentConfig,
        runner: SolidWorksAgentRunner | None = None,
    ) -> None:
        self._config = config
        self._runner = runner or SubprocessSolidWorksAgentRunner(config)

    def transfer(self, package: MappedSketchPackage) -> CadAdapterResult:
        request = build_solidworks_agent_request(package, self._config)
        response = self._runner.run(request)
        return parse_solidworks_agent_response(response)
