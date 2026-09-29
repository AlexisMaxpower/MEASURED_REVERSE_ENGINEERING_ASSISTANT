# Build / Reuse Check — Pass 4 Guided Capture Readiness

**Date:** 2026-09-30  
**Slice:** Chat 1 — Project & Guided Capture  
**Status:** isolated work package pending official OD-004 / Round-3 closure

## Problem

The slice already owns capture plan, clean reference, calibration, rectification, quality analysis and measurement-frame capture, but those primitives did not yet expose one deterministic answer to the UI/application layer:

> What must the user do next for this planned view, and is the required capture workflow complete?

## Reuse

No new CV, storage or contract technology is needed.

Reused existing Chat 1 state:

- `CaptureSession.views` and required/optional flags;
- immutable clean-reference `FrameRecord`;
- existing `CalibrationResult`;
- existing `CaptureQualityResult` / verdict;
- measurement-frame evidence;
- `CaptureViewStatus` acceptance state.

## Build

MREA-specific orchestration is implemented locally because this is product-domain policy, not a generic library problem:

- versioned `GuidedCapturePolicy`;
- deterministic `GuidedCaptureAction`;
- machine-readable blocker codes;
- per-view readiness state;
- session-level next required view/action;
- optional-view non-blocking semantics.

## Boundary rules

The readiness layer:

- does not create or alter physical measurements;
- does not infer geometry;
- does not alter calibration or quality values;
- does not mutate capture evidence;
- does not modify canonical contracts;
- does not claim that image quality is dimensional truth;
- remains a pure derivation over persisted Chat 1 state.

## Default workflow policy

For a non-accepted required view:

1. clean reference required;
2. calibration required;
3. quality analysis required;
4. rejected quality blocks progression;
5. WARN may proceed by default, but policy may require review;
6. at least one measurement frame required;
7. then the view is ready for explicit acceptance.

`OPTIONAL_3Q` and other non-required plan items do not prevent required-workflow completion.

## Why not change `CaptureSessionService.accept_view`

The existing acceptance API is kept backward-compatible. The new layer tells the application when acceptance is ready under the current guided policy without silently tightening an older persistence/API contract. A later approved migration may route UI acceptance exclusively through readiness checks.
