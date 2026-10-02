from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite

from .models import FeatureAnchor, MeasurementType, PhysicalMeasurement, ProvenanceSource
from .service import MeasurementSessionService
from .type_registry import MeasurementTypeRegistry


_OCR_VALUE_RE = re.compile(
    r"^(?P<value>[+-]?\d+(?:[.,]\d+)?)(?:\s*(?P<unit>mm|мм|deg|°))?$",
    re.IGNORECASE,
)
_OCR_NUMERIC_MENTION_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?")
_OCR_UNITS = {
    "mm": "mm",
    "мм": "mm",
    "deg": "deg",
    "°": "deg",
}


class OcrMeasurementError(ValueError):
    """Base class for fail-closed OCR measurement intake failures."""


class AmbiguousOcrMeasurement(OcrMeasurementError):
    """OCR text contains more than one plausible numeric measurement."""


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise OcrMeasurementError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise OcrMeasurementError(f"{field_name} must not be empty")
    return normalized


def _finite_coordinate(value: float | int, field_name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OcrMeasurementError(f"{field_name} must be numeric")
    normalized = float(value)
    if not isfinite(normalized):
        raise OcrMeasurementError(f"{field_name} must be finite")
    if positive:
        if normalized <= 0:
            raise OcrMeasurementError(f"{field_name} must be > 0")
    elif normalized < 0:
        raise OcrMeasurementError(f"{field_name} must be >= 0")
    return normalized


@dataclass(frozen=True, slots=True)
class DisplayRoi:
    """Provider-neutral LCD display region on one evidence frame in IMAGE_PX."""

    view_id: str
    evidence_frame_id: str
    x_px: float
    y_px: float
    width_px: float
    height_px: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(
            self,
            "evidence_frame_id",
            _non_empty(self.evidence_frame_id, "evidence_frame_id"),
        )
        object.__setattr__(self, "x_px", _finite_coordinate(self.x_px, "x_px"))
        object.__setattr__(self, "y_px", _finite_coordinate(self.y_px, "y_px"))
        object.__setattr__(
            self,
            "width_px",
            _finite_coordinate(self.width_px, "width_px", positive=True),
        )
        object.__setattr__(
            self,
            "height_px",
            _finite_coordinate(self.height_px, "height_px", positive=True),
        )


@dataclass(frozen=True, slots=True)
class OcrTextObservation:
    """Raw OCR-provider output tied to the exact display ROI that produced it."""

    text: str
    roi: DisplayRoi
    confidence: float | None = None
    provider_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _non_empty(self.text, "text"))
        if not isinstance(self.roi, DisplayRoi):
            raise OcrMeasurementError("roi must be DisplayRoi")
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
                raise OcrMeasurementError("confidence must be numeric")
            normalized = float(self.confidence)
            if not isfinite(normalized) or not 0.0 <= normalized <= 1.0:
                raise OcrMeasurementError("confidence must be finite and within [0, 1]")
            object.__setattr__(self, "confidence", normalized)
        if self.provider_id is not None:
            object.__setattr__(
                self,
                "provider_id",
                _non_empty(self.provider_id, "provider_id"),
            )


@dataclass(frozen=True, slots=True)
class OcrMeasurementProposal:
    """Validated OCR proposal. It is never a verified physical measurement by itself."""

    value: Decimal
    unit: str
    observation: OcrTextObservation
    source: ProvenanceSource = ProvenanceSource.OCR_MEASURED

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise OcrMeasurementError("OCR proposal value must be a finite Decimal")
        if self.unit not in {"mm", "deg"}:
            raise OcrMeasurementError(f"unsupported OCR proposal unit: {self.unit!r}")
        if self.source is not ProvenanceSource.OCR_MEASURED:
            raise OcrMeasurementError("OCR proposal source must be OCR_MEASURED")


@dataclass(frozen=True, slots=True)
class OcrMeasurementContext:
    """Physical-measurement context into which one OCR proposal may be inserted."""

    measurement_type: MeasurementType
    view_id: str
    anchor_a: FeatureAnchor
    anchor_b: FeatureAnchor | None = None
    anchor_c: FeatureAnchor | None = None
    evidence_frame_id: str | None = None
    uncertainty: Decimal | int | float | str | None = None
    uncertainty_mm: Decimal | int | float | str | None = None
    instrument_type: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        if not isinstance(self.measurement_type, MeasurementType):
            raise OcrMeasurementError("measurement_type must be MeasurementType")
        anchors = tuple(anchor for anchor in (self.anchor_a, self.anchor_b, self.anchor_c) if anchor)
        if not anchors:
            raise OcrMeasurementError("OCR measurement context requires at least one anchor")
        for anchor in anchors:
            if not isinstance(anchor, FeatureAnchor):
                raise OcrMeasurementError("OCR measurement anchors must be FeatureAnchor")
            if anchor.view_id != self.view_id:
                raise OcrMeasurementError("OCR measurement anchor view_id must match context view_id")
        if self.evidence_frame_id is None:
            raise OcrMeasurementError("OCR measurement context requires evidence_frame_id")
        object.__setattr__(
            self,
            "evidence_frame_id",
            _non_empty(self.evidence_frame_id, "evidence_frame_id"),
        )


class OcrMeasurementReader:
    """Deterministic provider-neutral validator for LCD OCR text.

    This layer deliberately does not correct OCR confusions such as ``O`` -> ``0``
    and does not verify measurements. It only produces an attributable candidate
    value when the OCR text has exactly one supported interpretation.
    """

    def __init__(self, type_registry: MeasurementTypeRegistry | None = None) -> None:
        self._type_registry = type_registry or MeasurementTypeRegistry()
        self._type_registry.validate_complete()

    def read(
        self,
        *,
        observation: OcrTextObservation,
        measurement_type: MeasurementType,
    ) -> OcrMeasurementProposal:
        if not isinstance(observation, OcrTextObservation):
            raise OcrMeasurementError("observation must be OcrTextObservation")

        normalized = self._normalize_ocr_text(observation.text)
        match = _OCR_VALUE_RE.fullmatch(normalized)
        if match is None:
            mentions = _OCR_NUMERIC_MENTION_RE.findall(normalized)
            if len(mentions) > 1:
                raise AmbiguousOcrMeasurement(
                    "OCR text contains multiple numeric values; refusing to choose one"
                )
            raise OcrMeasurementError(
                "OCR text is not an exact supported LCD measurement; no silent correction is allowed"
            )

        raw_value = match.group("value")
        value = Decimal(raw_value.replace(",", "."))
        if not value.is_finite():
            raise OcrMeasurementError("OCR value must be finite")

        expected_unit = self._type_registry.unit_for(measurement_type)
        raw_unit = match.group("unit")
        if raw_unit is not None:
            unit_hint = _OCR_UNITS[raw_unit.lower() if raw_unit != "°" else raw_unit]
            if unit_hint != expected_unit:
                raise OcrMeasurementError(
                    "explicit OCR unit does not match measurement type: "
                    f"ocr={unit_hint!r}, expected={expected_unit!r}"
                )

        return OcrMeasurementProposal(
            value=value,
            unit=expected_unit,
            observation=observation,
        )

    @staticmethod
    def _normalize_ocr_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text).strip().lower()
        normalized = normalized.replace("−", "-")
        normalized = " ".join(normalized.split())
        if not normalized:
            raise OcrMeasurementError("OCR text must not be empty")
        return normalized


class OcrMeasurementIntake:
    """Turn one validated OCR observation into an unverified session candidate."""

    def __init__(
        self,
        *,
        service: MeasurementSessionService,
        reader: OcrMeasurementReader | None = None,
    ) -> None:
        self._service = service
        self._reader = reader or OcrMeasurementReader()

    def propose_candidate(
        self,
        *,
        session_id: str,
        context: OcrMeasurementContext,
        observation: OcrTextObservation,
    ) -> PhysicalMeasurement:
        if observation.roi.view_id != context.view_id:
            raise OcrMeasurementError("OCR ROI view_id does not match measurement context")
        if observation.roi.evidence_frame_id != context.evidence_frame_id:
            raise OcrMeasurementError(
                "OCR ROI evidence_frame_id does not match measurement context"
            )

        proposal = self._reader.read(
            observation=observation,
            measurement_type=context.measurement_type,
        )
        measurement = self._service.add_reported_candidate(
            session_id=session_id,
            measurement_type=context.measurement_type,
            value=proposal.value,
            source=ProvenanceSource.OCR_MEASURED,
            view_id=context.view_id,
            anchor_a=context.anchor_a,
            anchor_b=context.anchor_b,
            anchor_c=context.anchor_c,
            evidence_frame_id=context.evidence_frame_id,
            uncertainty=context.uncertainty,
            uncertainty_mm=context.uncertainty_mm,
            instrument_type=context.instrument_type,
        )
        if measurement.is_verified:
            raise AssertionError("OCR intake must never auto-verify a measurement candidate")
        return measurement
