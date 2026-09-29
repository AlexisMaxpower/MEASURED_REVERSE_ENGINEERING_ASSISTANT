from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Mapping, AbstractSet


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    CONSTRAINT_CONFLICT = "CONSTRAINT_CONFLICT"


@dataclass(frozen=True, slots=True)
class ExpectedDimension:
    measurement_id: str
    expected_value_mm: float
    tolerance_mm: float

    def __post_init__(self) -> None:
        if not self.measurement_id:
            raise ValueError("measurement_id must not be empty")
        if not isfinite(self.expected_value_mm):
            raise ValueError("expected_value_mm must be finite")
        if not isfinite(self.tolerance_mm) or self.tolerance_mm < 0:
            raise ValueError("tolerance_mm must be finite and >= 0")


@dataclass(frozen=True, slots=True)
class DimensionVerification:
    measurement_id: str
    expected_value_mm: float
    actual_value_mm: float | None
    tolerance_mm: float
    delta_mm: float | None
    status: VerificationStatus


@dataclass(frozen=True, slots=True)
class VerificationReport:
    results: tuple[DimensionVerification, ...]

    def by_measurement_id(self) -> dict[str, DimensionVerification]:
        return {result.measurement_id: result for result in self.results}


class VerificationEngine:
    """Pure comparison logic.

    This model intentionally does not define the shared CADVerificationReport contract.
    A future boundary mapper must translate this internal report into the Integrator-owned
    contract once that schema exists.
    """

    def verify(
        self,
        expected: tuple[ExpectedDimension, ...],
        actual_values_mm: Mapping[str, float],
        constraint_conflicts: AbstractSet[str] = frozenset(),
    ) -> VerificationReport:
        seen: set[str] = set()
        results: list[DimensionVerification] = []

        for item in sorted(expected, key=lambda dim: dim.measurement_id):
            if item.measurement_id in seen:
                raise ValueError(f"duplicate expected measurement_id: {item.measurement_id}")
            seen.add(item.measurement_id)

            if item.measurement_id in constraint_conflicts:
                results.append(
                    DimensionVerification(
                        measurement_id=item.measurement_id,
                        expected_value_mm=item.expected_value_mm,
                        actual_value_mm=actual_values_mm.get(item.measurement_id),
                        tolerance_mm=item.tolerance_mm,
                        delta_mm=None,
                        status=VerificationStatus.CONSTRAINT_CONFLICT,
                    )
                )
                continue

            if item.measurement_id not in actual_values_mm:
                results.append(
                    DimensionVerification(
                        measurement_id=item.measurement_id,
                        expected_value_mm=item.expected_value_mm,
                        actual_value_mm=None,
                        tolerance_mm=item.tolerance_mm,
                        delta_mm=None,
                        status=VerificationStatus.MISSING,
                    )
                )
                continue

            actual = actual_values_mm[item.measurement_id]
            if not isfinite(actual):
                raise ValueError(f"actual value for {item.measurement_id} must be finite")

            delta = actual - item.expected_value_mm
            status = (
                VerificationStatus.VERIFIED
                if abs(delta) <= item.tolerance_mm
                else VerificationStatus.MISMATCH
            )
            results.append(
                DimensionVerification(
                    measurement_id=item.measurement_id,
                    expected_value_mm=item.expected_value_mm,
                    actual_value_mm=actual,
                    tolerance_mm=item.tolerance_mm,
                    delta_mm=delta,
                    status=status,
                )
            )

        return VerificationReport(results=tuple(results))
