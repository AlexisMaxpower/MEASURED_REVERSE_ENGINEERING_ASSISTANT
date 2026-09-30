from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import isfinite

from .hands_free import HandsFreeMeasurementController, HandsFreeTransition
from .models import ProvenanceSource


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


@dataclass(frozen=True, slots=True)
class OcrObservation:
    raw_text: str
    view_id: str
    reference_frame_id: str
    evidence_frame_id: str
    confidence: float | None = None
    provider_name: str | None = None

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
    """Deterministically parses a single physical value from provider OCR text."""

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
        if "," in numeric_token and "." in numeric_token:
            return OcrReadResult(
                status=OcrReadStatus.AMBIGUOUS,
                reason="mixed decimal separators are ambiguous",
            )

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
            ),
        )


class OcrMeasurementPipeline:
    """Bridges OCR text proposals into the existing explicit-confirmation state machine."""

    def __init__(
        self,
        *,
        reader: OcrMeasurementReader,
        controller: HandsFreeMeasurementController,
        expected_unit: str,
        view_id: str,
        reference_frame_id: str,
        evidence_frame_id: str,
    ) -> None:
        if expected_unit not in {"mm", "deg"}:
            raise ValueError("expected_unit must be 'mm' or 'deg'")
        for field_name, value in (
            ("view_id", view_id),
            ("reference_frame_id", reference_frame_id),
            ("evidence_frame_id", evidence_frame_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        self._reader = reader
        self._controller = controller
        self._expected_unit = expected_unit
        self._view_id = view_id
        self._reference_frame_id = reference_frame_id
        self._evidence_frame_id = evidence_frame_id

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
