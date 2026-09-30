from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import isfinite

from .hands_free import HandsFreeMeasurementController, HandsFreeTransition
from .models import ProvenanceSource
from .type_registry import MeasurementTypeRegistry


_NUMERIC_MENTION_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?")
_STRICT_VALUE_RE = re.compile(
    r"^([+-]?\d+(?:[.,]\d+)?)\s*(mm|мм|deg|°|град|градус|градуса|градусов)?$",
    re.IGNORECASE,
)


class OcrReadStatus(StrEnum):
    VALUE = "VALUE"
    NO_VALUE = "NO_VALUE"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID = "INVALID"
    UNIT_MISMATCH = "UNIT_MISMATCH"


def _validate_roi_bbox(bbox: tuple[float, float, float, float]) -> None:
    if len(bbox) != 4:
        raise ValueError("roi_bbox_px must contain x, y, width, height")
    x, y, width, height = bbox
    if any(not isfinite(float(value)) for value in bbox):
        raise ValueError("roi_bbox_px values must be finite")
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("roi_bbox_px must have non-negative origin and positive size")


@dataclass(frozen=True, slots=True)
class OcrObservation:
    raw_text: str
    view_id: str
    reference_frame_id: str
    evidence_frame_id: str
    confidence: float | None = None
    provider_name: str | None = None
    roi_id: str | None = None
    roi_bbox_px: tuple[float, float, float, float] | None = None
    roi_confidence: float | None = None
    roi_provider_name: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("raw_text", self.raw_text),
            ("view_id", self.view_id),
            ("reference_frame_id", self.reference_frame_id),
            ("evidence_frame_id", self.evidence_frame_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.confidence is not None:
            if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
                raise ValueError("OCR confidence must be within [0, 1]")
        if self.provider_name is not None and not self.provider_name.strip():
            raise ValueError("provider_name must be non-empty when supplied")

        roi_metadata_present = any(
            value is not None
            for value in (
                self.roi_id,
                self.roi_bbox_px,
                self.roi_confidence,
                self.roi_provider_name,
            )
        )
        if roi_metadata_present:
            if self.roi_id is None or not self.roi_id.strip():
                raise ValueError("roi_id is required when ROI metadata is supplied")
            if self.roi_bbox_px is None:
                raise ValueError("roi_bbox_px is required when ROI metadata is supplied")
            _validate_roi_bbox(self.roi_bbox_px)
            if self.roi_confidence is not None:
                if not isfinite(self.roi_confidence) or not 0 <= self.roi_confidence <= 1:
                    raise ValueError("ROI confidence must be within [0, 1]")
            if self.roi_provider_name is not None and not self.roi_provider_name.strip():
                raise ValueError("roi_provider_name must be non-empty when supplied")


@dataclass(frozen=True, slots=True)
class OcrMeasurementProposal:
    value: Decimal
    unit: str
    raw_text: str
    normalized_text: str
    view_id: str
    reference_frame_id: str
    evidence_frame_id: str
    confidence: float | None
    provider_name: str | None
    roi_id: str | None = None
    roi_bbox_px: tuple[float, float, float, float] | None = None
    roi_confidence: float | None = None
    roi_provider_name: str | None = None
    source: ProvenanceSource = ProvenanceSource.OCR_MEASURED


@dataclass(frozen=True, slots=True)
class OcrReadResult:
    status: OcrReadStatus
    proposal: OcrMeasurementProposal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is OcrReadStatus.VALUE and self.proposal is None:
            raise ValueError("VALUE OCR result requires a proposal")
        if self.status is not OcrReadStatus.VALUE and self.proposal is not None:
            raise ValueError("non-VALUE OCR result cannot carry a proposal")


@dataclass(frozen=True, slots=True)
class OcrPipelineResult:
    read: OcrReadResult
    transition: HandsFreeTransition | None = None

    def __post_init__(self) -> None:
        if self.read.status is OcrReadStatus.VALUE and self.transition is None:
            raise ValueError("VALUE OCR pipeline result requires a candidate transition")
        if self.read.status is not OcrReadStatus.VALUE and self.transition is not None:
            raise ValueError("non-VALUE OCR pipeline result cannot create a candidate")


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower().replace("ё", "е")
    return " ".join(normalized.split())


def _canonical_unit(token: str | None) -> str | None:
    if token is None:
        return None
    normalized = token.lower()
    if normalized in {"mm", "мм"}:
        return "mm"
    if normalized in {"deg", "°", "град", "градус", "градуса", "градусов"}:
        return "deg"
    raise AssertionError(f"unexpected OCR unit token: {token!r}")


class OcrMeasurementReader:
    """Deterministically parses one physical value from provider OCR text."""

    def read(self, observation: OcrObservation, *, expected_unit: str) -> OcrReadResult:
        if expected_unit not in {"mm", "deg"}:
            raise ValueError("expected_unit must be 'mm' or 'deg'")

        normalized = _normalize_text(observation.raw_text)
        mentions = _NUMERIC_MENTION_RE.findall(normalized)
        if not mentions:
            return OcrReadResult(
                status=OcrReadStatus.NO_VALUE,
                reason="OCR text contains no numeric value",
            )
        if len(mentions) > 1:
            return OcrReadResult(
                status=OcrReadStatus.AMBIGUOUS,
                reason="OCR text contains multiple numeric values",
            )

        match = _STRICT_VALUE_RE.fullmatch(normalized)
        if match is None:
            return OcrReadResult(
                status=OcrReadStatus.INVALID,
                reason="OCR text is not a strict value with an optional supported unit",
            )

        numeric_token, unit_token = match.groups()
        explicit_unit = _canonical_unit(unit_token)
        if explicit_unit is not None and explicit_unit != expected_unit:
            return OcrReadResult(
                status=OcrReadStatus.UNIT_MISMATCH,
                reason=f"OCR unit {explicit_unit!r} does not match expected unit {expected_unit!r}",
            )

        value = Decimal(numeric_token.replace(",", "."))
        if not value.is_finite():
            return OcrReadResult(
                status=OcrReadStatus.INVALID,
                reason="OCR numeric value must be finite",
            )

        return OcrReadResult(
            status=OcrReadStatus.VALUE,
            proposal=OcrMeasurementProposal(
                value=value,
                unit=expected_unit,
                raw_text=observation.raw_text,
                normalized_text=normalized,
                view_id=observation.view_id,
                reference_frame_id=observation.reference_frame_id,
                evidence_frame_id=observation.evidence_frame_id,
                confidence=observation.confidence,
                provider_name=observation.provider_name,
                roi_id=observation.roi_id,
                roi_bbox_px=observation.roi_bbox_px,
                roi_confidence=observation.roi_confidence,
                roi_provider_name=observation.roi_provider_name,
            ),
        )


class OcrMeasurementPipeline:
    """Bridges OCR proposals into the existing explicit-confirmation state machine."""

    def __init__(
        self,
        *,
        reader: OcrMeasurementReader,
        controller: HandsFreeMeasurementController,
        type_registry: MeasurementTypeRegistry | None = None,
    ) -> None:
        context = controller.context
        anchors = tuple(
            anchor
            for anchor in (context.anchor_a, context.anchor_b, context.anchor_c)
            if anchor is not None
        )
        reference_frame_ids = {anchor.reference_frame_id for anchor in anchors}
        if len(reference_frame_ids) != 1:
            raise ValueError("OCR measurement context anchors must use one reference frame")
        if context.evidence_frame_id is None:
            raise ValueError("OCR measurement context requires evidence_frame_id")

        registry = type_registry or MeasurementTypeRegistry()
        registry.validate_complete()

        self._reader = reader
        self._controller = controller
        self._expected_unit = registry.unit_for(context.measurement_type)
        self._view_id = context.view_id
        self._reference_frame_id = next(iter(reference_frame_ids))
        self._evidence_frame_id = context.evidence_frame_id

    @property
    def expected_unit(self) -> str:
        return self._expected_unit

    def process(self, observation: OcrObservation) -> OcrPipelineResult:
        if observation.view_id != self._view_id:
            raise ValueError("OCR observation view_id does not match measurement context")
        if observation.reference_frame_id != self._reference_frame_id:
            raise ValueError("OCR observation reference_frame_id does not match measurement context")
        if observation.evidence_frame_id != self._evidence_frame_id:
            raise ValueError("OCR observation evidence_frame_id does not match measurement context")

        read = self._reader.read(observation, expected_unit=self._expected_unit)
        if read.status is not OcrReadStatus.VALUE:
            return OcrPipelineResult(read=read)

        assert read.proposal is not None
        transition = self._controller.submit_candidate(
            value=read.proposal.value,
            source=ProvenanceSource.OCR_MEASURED,
        )
        return OcrPipelineResult(read=read, transition=transition)
