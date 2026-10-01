# Chat 1 — Pass 15 Voice-Triggered Measurement Capture

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-01-008`  
**Branch:** `chat-1/pass-15`  
**Baseline main:** `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`  
**Date:** 2026-10-01

## Scope

Pass 15 implements the first voice-trigger capture provenance slice already anticipated by the Chat-1 backlog and already accommodated by the canonical `MeasurementCaptureFrame.voice_event` field.

No shared contract change is required: `mrea.contracts.v1` already defines `voice_event` as `object | null`.

## Internal model

Added:

- `VoiceCaptureCommand.CAPTURE_MEASUREMENT_FRAME`;
- immutable `VoiceCaptureEvent` provenance with:
  - opaque `voice_event_id`;
  - fixed capture command;
  - timezone-aware `triggered_at`;
  - optional transcript;
  - optional locale.

`FrameRecord.voice_event` is optional and may only be attached to a `MEASUREMENT` frame. Capture-session validation rejects duplicate voice event IDs.

## Capture workflow

`CaptureSessionService.capture_measurement_frame_from_voice_trigger(...)` creates a voice event and stores it on the newly captured measurement frame while preserving the existing active clean-reference provenance.

Manual `capture_measurement_frame(...)` remains backward-compatible and persists `voice_event = None`.

A voice-triggered frame still requires an active clean reference. If none exists, capture fails without persisting an orphan frame/event.

## Canonical boundary

`CanonicalContractBuilder` now serializes a non-null voice event into the existing canonical field:

```json
{
  "event_id": "opaque UUID",
  "command": "CAPTURE_MEASUREMENT_FRAME",
  "triggered_at": "RFC3339 UTC timestamp",
  "transcript": "optional speech transcript",
  "locale": "optional locale"
}
```

This object records **capture-trigger provenance only**.

It does not represent or create a physical measurement, dimensional value, uncertainty, geometry inference, or `VOICE_REPORTED` measurement truth.

## Lineage behavior

Voice evidence follows the measurement frame to which it is attached.

When a clean reference is superseded, historical measurement frames and their voice events remain persisted, but the canonical active `CapturePackage` continues to emit only measurement frames belonging to the active clean-reference attempt.

## Tests

`tests/test_voice_trigger.py` covers:

1. persistence and canonical serialization of attributable voice-trigger provenance;
2. schema validation against the unchanged `CapturePackage v1` contract;
3. manual capture remains `voice_event = null`;
4. recapture preserves historical voice evidence while active canonical output excludes superseded-attempt measurement frames;
5. a voice trigger without an active clean reference fails without orphan persistence;
6. naive/non-timezone-aware trigger timestamps fail explicitly.

## Ownership / truth boundary

No shared contracts, canonical fixtures, Chat-6-owned CI, downstream measurement semantics, geometry, CAD or lifecycle truth are modified by this pass.
