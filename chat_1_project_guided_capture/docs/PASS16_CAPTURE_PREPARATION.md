# Chat 1 — Pass 16 Capture Preparation Preflight

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-01-008`  
**Branch:** `chat-1/pass-16`  
**Baseline main:** `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`  
**Date:** 2026-10-02

## Baseline / coordination note

At Pass-16 start, shared `main` still contains the certified Round-14 closure state. `chat-1/pass-15` exists and is ahead of `main`, but its own handoff marks it frozen and explicitly requires a later pass to start from the then-current certified `main` rather than from that worker branch.

Pass 16 therefore starts from current `main` and does not rewrite or mutate Pass 15. Central integration must evaluate both factual branch surfaces if Pass 15 has not been merged before Pass-16 review.

## Scope

Pass 16 implements the missing **background/object preparation** part of Chat-1 ownership as a deterministic, fail-closed pre-capture guidance surface.

The new `preparation.py` module evaluates operator-observed setup state before a clean-reference frame is captured. It checks:

- Measurement Mat readiness/visibility;
- object stability;
- background cleanliness;
- usable/even lighting;
- important-feature visibility / absence of occlusion.

Unknown required observations block readiness instead of being silently treated as success.

## Behavior

`CapturePreparationService.evaluate(...)` returns:

- whether setup is ready;
- all blocking findings in stable policy order;
- whether each finding is an explicit failure or an unconfirmed/unknown state;
- one deterministic next action corresponding to the first blocker;
- `CAPTURE_CLEAN_REFERENCE` only when every required preparation check passes.

`RussianCapturePreparationGuidanceAdapter` turns the machine-readable findings into actionable capture instructions without putting presentation text into policy state.

The evaluator is pure/read-only and deterministic: it does not mutate `CaptureSession`, source images, canonical packages or physical-measurement state.

## Policy / truth boundary

Policy version: `chat1.capture-preparation.v1`.

This surface records **operator preparation observations and guidance only**. It does not:

- claim CV detection of background, occlusion, stability or lighting;
- create or modify `PhysicalMeasurement`;
- infer dimensions or geometry;
- modify calibration/rectification evidence;
- change canonical `CapturePackage v1`;
- modify shared contracts, fixtures or adjacent slice code.

Individual checks can be explicitly disabled by policy for future product-specific workflows; required checks remain fail-closed for `None`/unknown state.

## Tests

`tests/test_preparation.py` covers:

1. all-required checks passing permits clean-reference capture;
2. unknown/failed checks block readiness;
3. finding and next-action priority is deterministic;
4. policy can explicitly make a check non-blocking;
5. evaluation is pure and repeatable;
6. Russian guidance differentiates failed vs unconfirmed preparation state.

Full Chat-1 plus adjacent contract/boundary CI remains the authoritative verification gate after publication.
