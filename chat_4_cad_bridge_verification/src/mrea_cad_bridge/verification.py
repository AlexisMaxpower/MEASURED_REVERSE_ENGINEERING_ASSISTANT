from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import AbstractSet, Mapping


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    CONSTRAINT_CONFLICT = "CONSTRAINT_CONFLICT"


@dataclass(frozen=True, slots=True)
class ExpectedDimension:
    dimension_id: str
    measurement_id: str | None
    expected_value: float
    unit: str
    tolerance: float

    def __post_init__(self) -> None:
        if not self.dimension_id:
            raise ValueError("dimension_id must not be empty")
        if self.measurement_id == "":
            raise ValueError("measurement_id must be null or non-empty")
        if self.unit not in {"mm", "deg"}:
            raise ValueError(f"unsupported unit: {self.unit}")
        if not isfinite(self.expected_value):
            raise ValueError("expected_value must be finite")
        if not isfinite(self.tolerance) or self.tolerance < 0:
            raise ValueError("tolerance must be finite and >= 0")


@dataclass(frozen=True, slots=True)
class DimensionVerification:
    dimension_id: str
    measurement_id: str | None
    expected_value: float
    actual_value: float | None
    unit: str
    tolerance: float
    difference: float | None
    status: VerificationStatus


@dataclass(frozen=True, slots=True)
class VerificationReport:
    results: tuple[DimensionVerification, ...]

    def by_dimension_id(self) -> dict[str, DimensionVerification]:
        return {result.dimension_id: result for result in self.results}


class VerificationEngine:
    """Pure numerical-transfer comparison keyed by canonical dimension_id."""

    def verify(
        self,
        expected: tuple[ExpectedDimension, ...],
        actual_values: Mapping[str, float],
        constraint_conflicts: AbstractSet[str] = frozenset(),
    ) -> VerificationReport:
        seen: set[str] = set()
        results: list[DimensionVerification] = []

        for item in expected:
            if item.dimension_id in seen:
                raise ValueError(f"duplicate expected dimension_id: {item.dimension_id}")
            seen.add(item.dimension_id)

            if item.dimension_id in constraint_conflicts:
                actual = actual_values.get(item.dimension_id)
                if actual is not None and not isfinite(actual):
                    raise ValueError(f"actual value for {item.dimension_id} must be finite")
                results.append(
                    DimensionVerification(
                        dimension_id=item.dimension_id,
                        measurement_id=item.measurement_id,
                        expected_value=item.expected_value,
                        actual_value=actual,
                        unit=item.unit,
                        tolerance=item.tolerance,
                        difference=None,
                        status=VerificationStatus.CONSTRAINT_CONFLICT,
                    )
                )
                continue

            if item.dimension_id not in actual_values:
                results.append(
                    DimensionVerification(
                        dimension_id=item.dimension_id,
                        measurement_id=item.measurement_id,
                        expected_value=item.expected_value,
                        actual_value=None,
                        unit=item.unit,
                        tolerance=item.tolerance,
                        difference=None,
                        status=VerificationStatus.MISSING,
                    )
                )
                continue

            actual = actual_values[item.dimension_id]
            if not isfinite(actual):
                raise ValueError(f"actual value for {item.dimension_id} must be finite")

            difference = abs(actual - item.expected_value)
            status = (
                VerificationStatus.VERIFIED
                if difference <= item.tolerance
                else VerificationStatus.MISMATCH
            )
            results.append(
                DimensionVerification(
                    dimension_id=item.dimension_id,
                    measurement_id=item.measurement_id,
                    expected_value=item.expected_value,
                    actual_value=actual,
                    unit=item.unit,
                    tolerance=item.tolerance,
                    difference=difference,
                    status=status,
                )
            )

        return VerificationReport(results=tuple(results))
