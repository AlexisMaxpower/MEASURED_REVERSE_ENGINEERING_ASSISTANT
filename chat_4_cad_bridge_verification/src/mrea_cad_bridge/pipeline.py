from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import (
    MappedSketchPackage,
    build_cad_package_v1,
    build_cad_verification_report_v1,
    map_sketch_package_v1,
)
from .verification import VerificationEngine, VerificationReport
from .vendor import CadAdapter, CadAdapterError, CadAdapterResult


@dataclass(frozen=True, slots=True)
class CadTransferExecution:
    mapped_sketch_package: MappedSketchPackage
    adapter_result: CadAdapterResult
    internal_verification: VerificationReport
    cad_package: dict[str, Any]
    cad_verification_report: dict[str, Any]


def execute_cad_transfer_v1(
    *,
    sketch_package: Mapping[str, Any],
    adapter: CadAdapter,
    cad_package_id: str,
    report_id: str,
) -> CadTransferExecution:
    """Run the canonical v1 CAD transfer boundary without vendor-specific policy."""

    mapped = map_sketch_package_v1(sketch_package)
    adapter_result = adapter.transfer(mapped)

    if adapter_result.adapter_name != adapter.adapter_name:
        raise CadAdapterError(
            f"adapter identity mismatch: interface={adapter.adapter_name!r}, "
            f"result={adapter_result.adapter_name!r}"
        )

    expected_by_id = {
        item.dimension_id: item for item in mapped.expected_dimensions
    }

    binding_ids = {binding.dimension_id for binding in adapter_result.bindings}
    unknown_bindings = binding_ids - set(expected_by_id)
    if unknown_bindings:
        raise CadAdapterError(
            "adapter returned bindings for unknown dimensions: "
            f"{sorted(unknown_bindings)!r}"
        )

    for binding in adapter_result.bindings:
        expected_measurement_id = expected_by_id[binding.dimension_id].measurement_id
        if binding.measurement_id != expected_measurement_id:
            raise CadAdapterError(
                f"measurement_id mismatch for {binding.dimension_id}: "
                f"expected {expected_measurement_id!r}, "
                f"got {binding.measurement_id!r}"
            )

    read_back_units = adapter_result.read_back.units()
    unknown_read_back = set(read_back_units) - set(expected_by_id)
    if unknown_read_back:
        raise CadAdapterError(
            "adapter returned unknown read-back dimension IDs: "
            f"{sorted(unknown_read_back)!r}"
        )

    for dimension_id, unit in read_back_units.items():
        expected_unit = expected_by_id[dimension_id].unit
        if unit != expected_unit:
            raise CadAdapterError(
                f"unit mismatch for {dimension_id}: "
                f"expected {expected_unit!r}, got {unit!r}"
            )

    internal_verification = VerificationEngine().verify(
        mapped.expected_dimensions,
        adapter_result.read_back.actual_values(),
        adapter_result.read_back.constraint_conflicts,
    )

    cad_package = build_cad_package_v1(
        cad_package_id=cad_package_id,
        sketch_package_id=mapped.sketch_package_id,
        adapter=adapter_result.adapter_name,
        artifacts=adapter_result.artifacts,
    )
    cad_verification_report = build_cad_verification_report_v1(
        report_id=report_id,
        cad_package_id=cad_package_id,
        sketch_package_id=mapped.sketch_package_id,
        report=internal_verification,
    )

    return CadTransferExecution(
        mapped_sketch_package=mapped,
        adapter_result=adapter_result,
        internal_verification=internal_verification,
        cad_package=cad_package,
        cad_verification_report=cad_verification_report,
    )
