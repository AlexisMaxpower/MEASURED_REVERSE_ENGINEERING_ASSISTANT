from __future__ import annotations

from math import isfinite
from typing import Mapping

from .contracts import MappedSketchPackage
from .vendor import (
    CadAdapterResult,
    CadDimensionBinding,
    CadReadBack,
    CadReadBackDimension,
)


class TestDoubleCadAdapter:
    """Deterministic vendor-neutral adapter used for canonical integration tests."""

    adapter_name = "TEST_DOUBLE"

    def __init__(
        self,
        *,
        actual_overrides: Mapping[str, float] | None = None,
        missing_readback_ids: frozenset[str] = frozenset(),
        constraint_conflicts: frozenset[str] = frozenset(),
    ) -> None:
        self._actual_overrides = dict(actual_overrides or {})
        self._missing_readback_ids = frozenset(missing_readback_ids)
        self._constraint_conflicts = frozenset(constraint_conflicts)

        for dimension_id, value in self._actual_overrides.items():
            if not dimension_id:
                raise ValueError("override dimension_id must not be empty")
            if not isfinite(value):
                raise ValueError(f"override for {dimension_id} must be finite")

    def transfer(self, package: MappedSketchPackage) -> CadAdapterResult:
        expected_by_id = {
            item.dimension_id: item for item in package.expected_dimensions
        }
        requested_ids = (
            set(self._actual_overrides)
            | set(self._missing_readback_ids)
            | set(self._constraint_conflicts)
        )
        unknown = requested_ids - set(expected_by_id)
        if unknown:
            raise ValueError(
                "test-double controls reference unknown dimension IDs: "
                f"{sorted(unknown)!r}"
            )

        bindings = tuple(
            CadDimensionBinding(
                dimension_id=item.dimension_id,
                measurement_id=item.measurement_id,
                vendor_dimension_ref=f"TEST_DOUBLE::DIM::{item.dimension_id}",
            )
            for item in package.expected_dimensions
        )

        dimensions = tuple(
            CadReadBackDimension(
                dimension_id=item.dimension_id,
                actual_value=self._actual_overrides.get(
                    item.dimension_id, item.expected_value
                ),
                unit=item.unit,
            )
            for item in package.expected_dimensions
            if item.dimension_id not in self._missing_readback_ids
        )

        return CadAdapterResult(
            adapter_name=self.adapter_name,
            bindings=bindings,
            read_back=CadReadBack(
                dimensions=dimensions,
                constraint_conflicts=self._constraint_conflicts,
            ),
            artifacts=(),
        )
