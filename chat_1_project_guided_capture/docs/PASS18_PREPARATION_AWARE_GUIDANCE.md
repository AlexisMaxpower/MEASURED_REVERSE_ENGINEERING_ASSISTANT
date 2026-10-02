# Chat 1 — Pass 18 Preparation-Aware Guided Capture Readiness

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-02-010`  
**Branch:** `chat-1/pass-18`  
**Baseline main:** `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`  
**Date:** 2026-10-02

## Scope

Pass 18 closes the remaining control-flow gap between the existing Guided Capture readiness layer and the prepared clean-reference gate accepted in Round 17.

Before this pass, the actual clean-reference mutation path was fail-closed on capture preparation, but the read-only `GuidedCaptureReadinessService` could still report `CAPTURE_CLEAN_REFERENCE` or `RECAPTURE_CLEAN_REFERENCE` without knowing whether preparation had been observed and passed.

Pass 18 adds an additive composition layer rather than changing the established persisted-evidence guidance contract.

## Preparation-aware guidance

Added `prepared_guidance.py` with:

- `PreparationAwareGuidedAction`;
- `PreparationAwareGuidedCaptureReadiness`;
- `PreparationAwareGuidedCaptureReadinessService`.

The service first derives the existing deterministic `GuidedCaptureReadiness` from persisted capture evidence.

If the next action is not clean-reference capture/recapture, the composed result preserves that action and does not require preparation.

If the next action is clean-reference capture or recapture, the composed layer fails closed:

1. no preparation observation -> `CHECK_PREPARATION`;
2. observation for the wrong guided view -> explicit `GuidedCaptureError`;
3. required failed/unknown preparation -> the deterministic corrective preparation action;
4. ready preparation -> the original guided capture action is released.

A ready preparation result therefore preserves the distinction between initial capture and recapture. The preparation evaluator itself still returns its generic `CAPTURE_CLEAN_REFERENCE` terminal action, while the composed layer retains `RECAPTURE_CLEAN_REFERENCE` when immutable lineage requires recapture.

## Read-only / truth boundary

The new service is read-only. It does not:

- create artifacts or frames;
- mutate `CaptureSession` or view state;
- alter active clean-reference lineage;
- persist preparation observations;
- create calibration, quality, measurement, geometry or CAD truth;
- change `CapturePackage v1` or shared contracts.

Preparation remains operator/setup guidance only. The authoritative fail-before-mutation enforcement remains `CapturePreparationCaptureService` from Pass 17.

## Compatibility

`GuidedCaptureReadinessService` remains unchanged as the lower-level persisted-evidence readiness primitive.

The new service is additive and exported through the Chat-1 package public API. Existing callers that intentionally need evidence-only readiness can continue using the original service; product flows that need one safe operator next-step surface can use the preparation-aware composition layer.

## Tests

`tests/test_prepared_guidance.py` covers:

1. missing preparation fails closed to `CHECK_PREPARATION` before initial capture guidance;
2. failed preparation exposes the deterministic corrective action;
3. ready preparation releases initial clean-reference capture;
4. ready preparation preserves recapture semantics after explicit reopen;
5. preparation observation must match the currently guided view;
6. non-capture actions are not unnecessarily gated by preparation;
7. composed guidance is deterministic, read-only and canonical-neutral.

Full Chat-1, canonical-contract and Chat-1 -> Chat-2 boundary CI are required before branch freeze.
