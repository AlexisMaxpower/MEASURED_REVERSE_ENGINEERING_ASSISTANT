# Chat 1 — Pass 17 Prepared Clean-Reference Gate

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-02-009`  
**Branch:** `chat-1/pass-17`  
**Baseline main:** `933d925c69944d40859ae1f9ff80d7a3ecb7f760`  
**Date:** 2026-10-02

## Scope

Pass 17 connects the accepted Pass-16 capture-preparation preflight to the actual clean-reference mutation path.

Pass 16 intentionally implemented a pure fail-closed evaluator. Pass 17 adds an application facade so the guided product flow can enforce that evaluator before either an initial clean-reference capture or a clean-reference recapture.

## Prepared capture facade

Added `CapturePreparationCaptureService` with:

- `capture_clean_reference(...)`;
- `recapture_clean_reference(...)`.

Both methods:

1. evaluate the supplied `CapturePreparationObservation` using the existing versioned preparation policy;
2. fail before calling the underlying capture service when any required check is failed or unknown;
3. call the existing `CaptureSessionService` only after preparation is ready;
4. return `PreparedCleanReferenceCapture`, coupling the ephemeral preparation result with the resulting immutable clean-reference frame.

`CapturePreparationGateError` exposes the machine-readable blocked `CapturePreparationResult`, allowing UI/orchestration to render the already-defined corrective action and Russian guidance.

## Failure atomicity

A blocked preflight does not:

- create an image artifact;
- append a frame;
- move the active clean-reference pointer;
- mutate view status;
- create calibration/quality/measurement evidence.

The check therefore fails before the capture mutation boundary.

## Recapture / lineage

The same preparation gate is applied to recapture.

Once preparation passes, recapture delegates to the existing immutable lineage behavior. The new frame still records `supersedes_frame_id`, historical evidence remains intact, and only the active pointer advances.

The facade does not bypass the existing accepted-view reopen rule or any other `CaptureSessionService` guard.

## Compatibility

The lower-level `CaptureSessionService.capture_clean_reference(...)` and `recapture_clean_reference(...)` APIs remain unchanged for backward compatibility and internal composition.

Pass 17 also exports the Pass-16 preparation models/services plus the new prepared-capture facade through the package public API.

## Canonical / truth boundary

Preparation remains operator/setup guidance only.

The ephemeral preparation result is not persisted into `CaptureSession` and is not emitted into `CapturePackage v1`. The canonical schema, fixtures and downstream physical-measurement semantics are unchanged.

No preparation observation or successful gate result is promoted to:

- physical measurement truth;
- calibration truth;
- geometry inference;
- CAD verification;
- lifecycle knowledge.

## Tests

`tests/test_preparation_capture.py` covers:

1. failed/unknown preparation blocks before session or artifact mutation;
2. ready preparation permits initial clean-reference capture;
3. recapture is gated by the same preparation policy;
4. successful recapture preserves immutable supersession lineage;
5. prepared capture does not add preparation state to canonical `CapturePackage v1`.

Full Chat-1, canonical-contract and Chat-1 → Chat-2 boundary CI are required before branch freeze.
