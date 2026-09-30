from __future__ import annotations

from .models import (
    CalibrationResult,
    CaptureSession,
    CaptureViewType,
    FrameKind,
    FrameRecord,
    RectifiedReferenceRecord,
)


class CaptureLineageError(RuntimeError):
    pass


def active_clean_reference(
    session: CaptureSession,
    view: CaptureViewType,
) -> FrameRecord | None:
    progress = next((item for item in session.views if item.view is view), None)
    if progress is None:
        raise CaptureLineageError(f"view {view.value} is not part of the capture session")
    frame_id = progress.active_clean_reference_frame_id
    if frame_id is None:
        return None
    frame = next((item for item in session.frames if item.frame_id == frame_id), None)
    if frame is None or frame.kind is not FrameKind.CLEAN_REFERENCE or frame.view is not view:
        raise CaptureLineageError(f"active clean reference is invalid for view {view.value}")
    return frame


def calibration_for_active_reference(
    session: CaptureSession,
    view: CaptureViewType,
) -> CalibrationResult | None:
    clean = active_clean_reference(session, view)
    if clean is None:
        return None
    matches = [item for item in session.calibrations if item.source_frame_id == clean.frame_id]
    if len(matches) > 1:
        raise CaptureLineageError(f"active clean reference has multiple calibrations for {view.value}")
    return matches[0] if matches else None


def rectification_for_active_reference(
    session: CaptureSession,
    view: CaptureViewType,
) -> RectifiedReferenceRecord | None:
    clean = active_clean_reference(session, view)
    if clean is None:
        return None
    matches = [
        item for item in session.rectified_references if item.source_frame_id == clean.frame_id
    ]
    if len(matches) > 1:
        raise CaptureLineageError(
            f"active clean reference has multiple rectifications for {view.value}"
        )
    return matches[0] if matches else None


def measurement_frames_for_active_reference(
    session: CaptureSession,
    view: CaptureViewType,
) -> list[FrameRecord]:
    clean = active_clean_reference(session, view)
    if clean is None:
        return []
    return [
        frame
        for frame in session.frames
        if frame.view is view
        and frame.kind is FrameKind.MEASUREMENT
        and frame.source_clean_reference_frame_id == clean.frame_id
    ]
