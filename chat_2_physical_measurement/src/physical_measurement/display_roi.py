from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Iterable

from .models import ProvenanceSource
from .ocr import OcrObservation


class RoiSelectionStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class DisplayRoiCandidate:
    roi_id: str
    view_id: str
    reference_frame_id: str
    evidence_frame_id: str
    x_px: float
    y_px: float
    width_px: float
    height_px: float
    confidence: float
    provider_name: str | None = None
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED

    def __post_init__(self) -> None:
        for field_name, value in (
            ("roi_id", self.roi_id),
            ("view_id", self.view_id),
            ("reference_frame_id", self.reference_frame_id),
            ("evidence_frame_id", self.evidence_frame_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name, value in (
            ("x_px", self.x_px),
            ("y_px", self.y_px),
            ("width_px", self.width_px),
            ("height_px", self.height_px),
            ("confidence", self.confidence),
        ):
            if not isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite")
        if self.x_px < 0 or self.y_px < 0:
            raise ValueError("ROI origin must be >= 0")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("ROI width/height must be > 0")
        if not 0 <= self.confidence <= 1:
            raise ValueError("ROI confidence must be within [0, 1]")
        if self.provider_name is not None and not self.provider_name.strip():
            raise ValueError("provider_name must be non-empty when supplied")
        if self.source is not ProvenanceSource.VISION_DETECTED:
            raise ValueError("display ROI candidates must use VISION_DETECTED provenance")

    @property
    def bbox_px(self) -> tuple[float, float, float, float]:
        return (self.x_px, self.y_px, self.width_px, self.height_px)


@dataclass(frozen=True, slots=True)
class DisplayRoiProposal:
    roi_id: str
    view_id: str
    reference_frame_id: str
    evidence_frame_id: str
    bbox_px: tuple[float, float, float, float]
    confidence: float
    provider_name: str | None
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED

    def __post_init__(self) -> None:
        if self.source is not ProvenanceSource.VISION_DETECTED:
            raise ValueError("display ROI proposal must use VISION_DETECTED provenance")
        if len(self.bbox_px) != 4:
            raise ValueError("ROI bbox must contain x, y, width, height")
        x, y, width, height = self.bbox_px
        if any(not isfinite(float(value)) for value in self.bbox_px):
            raise ValueError("ROI bbox values must be finite")
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError("ROI bbox must have non-negative origin and positive size")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("ROI confidence must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class DisplayRoiSelection:
    status: RoiSelectionStatus
    proposal: DisplayRoiProposal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is RoiSelectionStatus.MATCH and self.proposal is None:
            raise ValueError("MATCH ROI selection requires a proposal")
        if self.status is not RoiSelectionStatus.MATCH and self.proposal is not None:
            raise ValueError("non-MATCH ROI selection cannot carry a proposal")


class DisplayRoiSelector:
    """Provider-neutral deterministic display-ROI selection policy."""

    def __init__(self, *, min_confidence: float = 0.0, ambiguity_epsilon: float = 0.02) -> None:
        if not isfinite(min_confidence) or not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be within [0, 1]")
        if not isfinite(ambiguity_epsilon) or ambiguity_epsilon < 0:
            raise ValueError("ambiguity_epsilon must be >= 0")
        self._min_confidence = min_confidence
        self._ambiguity_epsilon = ambiguity_epsilon

    def select(
        self,
        candidates: Iterable[DisplayRoiCandidate],
        *,
        view_id: str,
        reference_frame_id: str,
        evidence_frame_id: str,
    ) -> DisplayRoiSelection:
        values = tuple(candidates)
        ids = [candidate.roi_id for candidate in values]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate display ROI candidate ids are not allowed")

        eligible = [
            candidate
            for candidate in values
            if candidate.view_id == view_id
            and candidate.reference_frame_id == reference_frame_id
            and candidate.evidence_frame_id == evidence_frame_id
            and candidate.confidence >= self._min_confidence
        ]
        if not eligible:
            return DisplayRoiSelection(
                status=RoiSelectionStatus.NO_MATCH,
                reason="no display ROI candidate matches the active evidence context",
            )

        eligible.sort(key=lambda candidate: (-candidate.confidence, candidate.roi_id))
        best = eligible[0]
        if len(eligible) > 1:
            second = eligible[1]
            if abs(best.confidence - second.confidence) <= self._ambiguity_epsilon:
                return DisplayRoiSelection(
                    status=RoiSelectionStatus.AMBIGUOUS,
                    reason="top display ROI candidates are within ambiguity epsilon",
                )

        return DisplayRoiSelection(
            status=RoiSelectionStatus.MATCH,
            proposal=DisplayRoiProposal(
                roi_id=best.roi_id,
                view_id=best.view_id,
                reference_frame_id=best.reference_frame_id,
                evidence_frame_id=best.evidence_frame_id,
                bbox_px=best.bbox_px,
                confidence=best.confidence,
                provider_name=best.provider_name,
            ),
        )


class DisplayRoiOcrBridge:
    """Builds an OCR observation from one explicitly selected display ROI."""

    @staticmethod
    def build_observation(
        *,
        proposal: DisplayRoiProposal,
        raw_text: str,
        ocr_confidence: float | None = None,
        ocr_provider_name: str | None = None,
    ) -> OcrObservation:
        return OcrObservation(
            raw_text=raw_text,
            view_id=proposal.view_id,
            reference_frame_id=proposal.reference_frame_id,
            evidence_frame_id=proposal.evidence_frame_id,
            confidence=ocr_confidence,
            provider_name=ocr_provider_name,
            roi_id=proposal.roi_id,
            roi_bbox_px=proposal.bbox_px,
            roi_confidence=proposal.confidence,
            roi_provider_name=proposal.provider_name,
        )
