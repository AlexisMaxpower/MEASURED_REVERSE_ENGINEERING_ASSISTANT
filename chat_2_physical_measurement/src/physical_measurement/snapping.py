from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot, isfinite
from typing import Iterable

from .models import FeatureAnchor, ProvenanceSource


class SnapSelectionStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class FeatureSnapCandidate:
    feature_id: str
    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float
    confidence: float | None = None
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED

    def __post_init__(self) -> None:
        for field_name, value in (
            ("feature_id", self.feature_id),
            ("view_id", self.view_id),
            ("reference_frame_id", self.reference_frame_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isfinite(self.x_px) or not isfinite(self.y_px):
            raise ValueError("snap candidate coordinates must be finite")
        if self.x_px < 0 or self.y_px < 0:
            raise ValueError("snap candidate coordinates must be >= 0")
        if self.confidence is not None:
            if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
                raise ValueError("confidence must be within [0, 1]")
        if self.source is not ProvenanceSource.VISION_DETECTED:
            raise ValueError("feature snap candidates must use VISION_DETECTED provenance")


@dataclass(frozen=True, slots=True)
class FeatureSnapProposal:
    anchor_id: str
    feature_id: str
    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float
    distance_px: float
    confidence: float | None
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED


@dataclass(frozen=True, slots=True)
class FeatureSnapSelection:
    status: SnapSelectionStatus
    proposal: FeatureSnapProposal | None = None
    competing_feature_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status is SnapSelectionStatus.MATCH and self.proposal is None:
            raise ValueError("MATCH selection requires a proposal")
        if self.status is not SnapSelectionStatus.MATCH and self.proposal is not None:
            raise ValueError("non-MATCH selection cannot carry a proposal")
        if self.status is SnapSelectionStatus.AMBIGUOUS and len(self.competing_feature_ids) < 2:
            raise ValueError("AMBIGUOUS selection requires at least two feature ids")


class FeatureAnchorSelector:
    """Provider-independent nearest-feature selector with explicit ambiguity handling."""

    def __init__(self, *, max_distance_px: float, ambiguity_epsilon_px: float = 0.25) -> None:
        if not isfinite(max_distance_px) or max_distance_px <= 0:
            raise ValueError("max_distance_px must be finite and > 0")
        if not isfinite(ambiguity_epsilon_px) or ambiguity_epsilon_px < 0:
            raise ValueError("ambiguity_epsilon_px must be finite and >= 0")
        self._max_distance_px = max_distance_px
        self._ambiguity_epsilon_px = ambiguity_epsilon_px

    def select(
        self,
        *,
        anchor: FeatureAnchor,
        candidates: Iterable[FeatureSnapCandidate],
    ) -> FeatureSnapSelection:
        seen_feature_ids: set[str] = set()
        ranked: list[tuple[float, FeatureSnapCandidate]] = []

        for candidate in candidates:
            if candidate.feature_id in seen_feature_ids:
                raise ValueError(f"duplicate feature_id in snap candidates: {candidate.feature_id}")
            seen_feature_ids.add(candidate.feature_id)

            if candidate.view_id != anchor.view_id:
                continue
            if candidate.reference_frame_id != anchor.reference_frame_id:
                continue

            distance = hypot(candidate.x_px - anchor.x_px, candidate.y_px - anchor.y_px)
            if distance <= self._max_distance_px:
                ranked.append((distance, candidate))

        if not ranked:
            return FeatureSnapSelection(status=SnapSelectionStatus.NO_MATCH)

        ranked.sort(key=lambda item: (item[0], item[1].feature_id))
        best_distance, best = ranked[0]
        competing = [
            candidate.feature_id
            for distance, candidate in ranked
            if distance - best_distance <= self._ambiguity_epsilon_px
        ]

        if len(competing) > 1:
            return FeatureSnapSelection(
                status=SnapSelectionStatus.AMBIGUOUS,
                competing_feature_ids=tuple(sorted(competing)),
            )

        return FeatureSnapSelection(
            status=SnapSelectionStatus.MATCH,
            proposal=FeatureSnapProposal(
                anchor_id=anchor.anchor_id,
                feature_id=best.feature_id,
                view_id=best.view_id,
                reference_frame_id=best.reference_frame_id,
                x_px=best.x_px,
                y_px=best.y_px,
                distance_px=best_distance,
                confidence=best.confidence,
            ),
        )
