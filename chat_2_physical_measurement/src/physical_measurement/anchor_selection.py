from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isclose, isfinite
from typing import Iterable

from .models import FeatureAnchor, ProvenanceSource


class AnchorSelectionError(ValueError):
    """Base class for deterministic feature-anchor selection failures."""


class AmbiguousAnchorSnap(AnchorSelectionError):
    """More than one equally-near snap target is plausible for the same manual pick."""


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise AnchorSelectionError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise AnchorSelectionError(f"{field_name} must not be empty")
    return normalized


def _coordinate(value: float | int, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnchorSelectionError(f"{field_name} must be numeric")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0:
        raise AnchorSelectionError(f"{field_name} must be finite and >= 0")
    return normalized


@dataclass(frozen=True, slots=True)
class ManualAnchorPick:
    """Raw IMAGE_PX point selected by the operator before any snapping suggestion."""

    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(
            self,
            "reference_frame_id",
            _non_empty(self.reference_frame_id, "reference_frame_id"),
        )
        object.__setattr__(self, "x_px", _coordinate(self.x_px, "x_px"))
        object.__setattr__(self, "y_px", _coordinate(self.y_px, "y_px"))


@dataclass(frozen=True, slots=True)
class AnchorSnapTarget:
    """Provider-neutral detected feature offered only as a snapping suggestion."""

    target_id: str
    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float
    source: ProvenanceSource = ProvenanceSource.VISION_DETECTED

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _non_empty(self.target_id, "target_id"))
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(
            self,
            "reference_frame_id",
            _non_empty(self.reference_frame_id, "reference_frame_id"),
        )
        object.__setattr__(self, "x_px", _coordinate(self.x_px, "x_px"))
        object.__setattr__(self, "y_px", _coordinate(self.y_px, "y_px"))
        if self.source is not ProvenanceSource.VISION_DETECTED:
            raise AnchorSelectionError(
                "snap target source must be VISION_DETECTED; detected features are advisory only"
            )


@dataclass(frozen=True, slots=True)
class AnchorSnapProposal:
    """Non-mutating proposal connecting a manual pick to one nearby detected feature."""

    raw_pick: ManualAnchorPick
    target: AnchorSnapTarget
    distance_px: float
    snap_radius_px: float

    def __post_init__(self) -> None:
        if self.target.view_id != self.raw_pick.view_id:
            raise AnchorSelectionError("snap proposal view_id must match the raw pick")
        if self.target.reference_frame_id != self.raw_pick.reference_frame_id:
            raise AnchorSelectionError(
                "snap proposal reference_frame_id must match the raw pick"
            )
        if not isfinite(self.distance_px) or self.distance_px < 0:
            raise AnchorSelectionError("distance_px must be finite and >= 0")
        if not isfinite(self.snap_radius_px) or self.snap_radius_px <= 0:
            raise AnchorSelectionError("snap_radius_px must be finite and > 0")
        if self.distance_px > self.snap_radius_px:
            raise AnchorSelectionError("snap proposal target lies outside snap radius")


@dataclass(frozen=True, slots=True)
class FeatureAnchorSelection:
    """Explicit final anchor placement decision in IMAGE_PX.

    For a manual keep-raw decision the source is ``MANUAL_MEASURED``. For an
    accepted snap the source remains ``VISION_DETECTED`` and the distinct
    ``confirmation_source`` records ``USER_CONFIRMED``. This prevents the
    detector contribution from being relabelled as manual truth.

    The existing ``FeatureAnchor`` model does not yet persist this selection
    provenance. Callers that need the provenance must retain this decision object
    alongside the materialized anchor until a dedicated durable-anchor metadata
    migration is approved.
    """

    view_id: str
    reference_frame_id: str
    x_px: float
    y_px: float
    raw_x_px: float
    raw_y_px: float
    source: ProvenanceSource
    confirmation_source: ProvenanceSource | None = None
    snap_target_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _non_empty(self.view_id, "view_id"))
        object.__setattr__(
            self,
            "reference_frame_id",
            _non_empty(self.reference_frame_id, "reference_frame_id"),
        )
        for field_name in ("x_px", "y_px", "raw_x_px", "raw_y_px"):
            object.__setattr__(self, field_name, _coordinate(getattr(self, field_name), field_name))

        if self.snap_target_id is None:
            if self.source is not ProvenanceSource.MANUAL_MEASURED:
                raise AnchorSelectionError(
                    "unsnapped anchor selection source must be MANUAL_MEASURED"
                )
            if self.confirmation_source is not None:
                raise AnchorSelectionError(
                    "unsnapped manual anchor selection must not invent confirmation provenance"
                )
            return

        object.__setattr__(
            self,
            "snap_target_id",
            _non_empty(self.snap_target_id, "snap_target_id"),
        )
        if self.source is not ProvenanceSource.VISION_DETECTED:
            raise AnchorSelectionError(
                "snapped anchor selection source must remain VISION_DETECTED"
            )
        if self.confirmation_source is not ProvenanceSource.USER_CONFIRMED:
            raise AnchorSelectionError(
                "snapped anchor selection requires USER_CONFIRMED confirmation provenance"
            )

    @property
    def snapped(self) -> bool:
        return self.snap_target_id is not None

    def build_anchor(self, *, anchor_id: str) -> FeatureAnchor:
        """Materialize the explicit placement as the existing internal FeatureAnchor."""

        return FeatureAnchor(
            anchor_id=anchor_id,
            view_id=self.view_id,
            reference_frame_id=self.reference_frame_id,
            x_px=self.x_px,
            y_px=self.y_px,
        )


class FeatureAnchorSelector:
    """Deterministic, fail-closed snap proposal and explicit-acceptance workflow."""

    def propose_snap(
        self,
        *,
        raw_pick: ManualAnchorPick,
        targets: Iterable[AnchorSnapTarget],
        snap_radius_px: float,
    ) -> AnchorSnapProposal | None:
        radius = _coordinate(snap_radius_px, "snap_radius_px")
        if radius <= 0:
            raise AnchorSelectionError("snap_radius_px must be > 0")

        seen_ids: set[str] = set()
        eligible: list[tuple[float, AnchorSnapTarget]] = []
        for target in targets:
            if not isinstance(target, AnchorSnapTarget):
                raise AnchorSelectionError("targets must contain AnchorSnapTarget values")
            if target.target_id in seen_ids:
                raise AnchorSelectionError(f"duplicate snap target_id: {target.target_id}")
            seen_ids.add(target.target_id)

            if target.view_id != raw_pick.view_id:
                continue
            if target.reference_frame_id != raw_pick.reference_frame_id:
                continue
            distance = hypot(target.x_px - raw_pick.x_px, target.y_px - raw_pick.y_px)
            if distance <= radius:
                eligible.append((distance, target))

        if not eligible:
            return None

        nearest_distance = min(distance for distance, _ in eligible)
        nearest = [
            target
            for distance, target in eligible
            if isclose(distance, nearest_distance, rel_tol=0.0, abs_tol=1e-9)
        ]
        if len(nearest) != 1:
            raise AmbiguousAnchorSnap(
                "multiple equally-near snap targets require explicit target selection"
            )

        target = nearest[0]
        return AnchorSnapProposal(
            raw_pick=raw_pick,
            target=target,
            distance_px=nearest_distance,
            snap_radius_px=radius,
        )

    def keep_raw(self, *, raw_pick: ManualAnchorPick) -> FeatureAnchorSelection:
        """Use the operator's original IMAGE_PX point without snapping."""

        return FeatureAnchorSelection(
            view_id=raw_pick.view_id,
            reference_frame_id=raw_pick.reference_frame_id,
            x_px=raw_pick.x_px,
            y_px=raw_pick.y_px,
            raw_x_px=raw_pick.x_px,
            raw_y_px=raw_pick.y_px,
            source=ProvenanceSource.MANUAL_MEASURED,
        )

    def accept_snap(
        self,
        *,
        proposal: AnchorSnapProposal,
        explicit_user_confirmation: bool,
    ) -> FeatureAnchorSelection:
        """Accept one proposal only through an explicit operator-confirmation transition."""

        if explicit_user_confirmation is not True:
            raise AnchorSelectionError("snap acceptance requires explicit user confirmation")
        return FeatureAnchorSelection(
            view_id=proposal.raw_pick.view_id,
            reference_frame_id=proposal.raw_pick.reference_frame_id,
            x_px=proposal.target.x_px,
            y_px=proposal.target.y_px,
            raw_x_px=proposal.raw_pick.x_px,
            raw_y_px=proposal.raw_pick.y_px,
            source=proposal.target.source,
            confirmation_source=ProvenanceSource.USER_CONFIRMED,
            snap_target_id=proposal.target.target_id,
        )
