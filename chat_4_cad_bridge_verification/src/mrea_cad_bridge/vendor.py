from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts import MappedSketchPackage


class CadAdapterError(RuntimeError):
    """Raised when a vendor adapter violates the normalized CAD boundary."""


@dataclass(frozen=True, slots=True)
class CadDimensionBinding:
    dimension_id: str
    measurement_id: str | None
    vendor_dimension_ref: str

    def __post_init__(self) -> None:
        if not self.dimension_id:
            raise ValueError("dimension_id must not be empty")
        if self.measurement_id == "":
            raise ValueError("measurement_id must be null or non-empty")
        if not self.vendor_dimension_ref:
            raise ValueError("vendor_dimension_ref must not be empty")


@dataclass(frozen=True, slots=True)
class CadReadBackDimension:
    dimension_id: str
    actual_value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.dimension_id:
            raise ValueError("dimension_id must not be empty")
        if self.unit not in {"mm", "deg"}:
            raise ValueError(f"unsupported unit: {self.unit}")
        if not isfinite(self.actual_value):
            raise ValueError("actual_value must be finite")


@dataclass(frozen=True, slots=True)
class CadReadBack:
    dimensions: tuple[CadReadBackDimension, ...]
    constraint_conflicts: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        ids = [item.dimension_id for item in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("read-back dimension_id values must be unique")
        if any(not dimension_id for dimension_id in self.constraint_conflicts):
            raise ValueError("constraint conflict dimension IDs must not be empty")

    def actual_values(self) -> dict[str, float]:
        return {item.dimension_id: item.actual_value for item in self.dimensions}

    def units(self) -> dict[str, str]:
        return {item.dimension_id: item.unit for item in self.dimensions}


_ARTIFACT_REFERENCE_FIELDS = frozenset(
    {"artifact_id", "kind", "uri", "media_type", "sha256", "metadata"}
)
_ARTIFACT_REFERENCE_REQUIRED_FIELDS = ("artifact_id", "kind", "uri")


def _validate_artifact_reference(artifact: Mapping[str, Any], *, index: int) -> str:
    if not isinstance(artifact, Mapping):
        raise ValueError(f"artifact[{index}] must be a mapping")

    extra_fields = set(artifact) - _ARTIFACT_REFERENCE_FIELDS
    if extra_fields:
        raise ValueError(
            f"artifact[{index}] contains unsupported fields: {sorted(extra_fields)!r}"
        )

    for field in _ARTIFACT_REFERENCE_REQUIRED_FIELDS:
        value = artifact.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"artifact[{index}].{field} must be a non-empty string")

    media_type = artifact.get("media_type")
    if media_type is not None and not isinstance(media_type, str):
        raise ValueError(f"artifact[{index}].media_type must be string or null")

    sha256 = artifact.get("sha256")
    if sha256 is not None and not isinstance(sha256, str):
        raise ValueError(f"artifact[{index}].sha256 must be string or null")

    if "metadata" in artifact and not isinstance(artifact["metadata"], Mapping):
        raise ValueError(f"artifact[{index}].metadata must be an object")

    return artifact["artifact_id"]


@dataclass(frozen=True, slots=True)
class CadAdapterResult:
    adapter_name: str
    bindings: tuple[CadDimensionBinding, ...]
    read_back: CadReadBack
    artifacts: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.adapter_name:
            raise ValueError("adapter_name must not be empty")

        dimension_ids = [binding.dimension_id for binding in self.bindings]
        vendor_refs = [binding.vendor_dimension_ref for binding in self.bindings]
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ValueError("dimension bindings must have unique dimension_id values")
        if len(vendor_refs) != len(set(vendor_refs)):
            raise ValueError("dimension bindings must have unique vendor_dimension_ref values")

        known_ids = set(dimension_ids)
        unknown_read_back = set(self.read_back.actual_values()) - known_ids
        unknown_conflicts = set(self.read_back.constraint_conflicts) - known_ids
        if unknown_read_back:
            raise ValueError(
                f"read-back contains unbound dimensions: {sorted(unknown_read_back)!r}"
            )
        if unknown_conflicts:
            raise ValueError(
                f"constraint conflicts contain unbound dimensions: {sorted(unknown_conflicts)!r}"
            )

        artifact_ids = [
            _validate_artifact_reference(artifact, index=index)
            for index, artifact in enumerate(self.artifacts)
        ]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("artifact_id values must be unique")


class CadAdapter(Protocol):
    adapter_name: str

    def transfer(self, package: "MappedSketchPackage") -> CadAdapterResult:
        ...
