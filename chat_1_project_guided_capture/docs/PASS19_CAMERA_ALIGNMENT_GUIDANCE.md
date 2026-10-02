# Chat 1 — Pass 19 Camera Alignment Guidance

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-02-011`  
**Branch:** `chat-1/pass-19`  
**Baseline main:** `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`  
**Date:** 2026-10-02

## Scope

Pass 19 closes two still-unimplemented Guided Capture checks named by the Chat-1 SSOT:

- camera tilt;
- perspective distortion.

The implementation is deliberately a read-only guidance evaluator over already-existing active clean-reference, camera-metadata and calibration evidence. It does not estimate physical dimensions and does not claim a recovered physical camera pose.

## Added service

`CaptureAlignmentService` evaluates the active clean reference for a view and requires calibration tied to that exact active reference.

Inputs are existing Chat-1 evidence only:

- active clean-reference frame identity;
- source image width/height from `CameraMetadata`;
- active `CalibrationResult` homography (`IMAGE_PX -> MAT_XY_MM`).

Outputs are an ephemeral `CaptureAlignmentResult` with:

- deterministic `alignment_id`;
- source frame and calibration provenance;
- versioned policy identity;
- dimensionless alignment metrics;
- machine-readable findings;
- `ACCEPT`, `WARN` or `REJECT` guidance verdict;
- one actionable next step derived from the first deterministic finding.

## Metrics

### Camera-tilt proxy

The evaluator computes the local homography Jacobian at the source-frame centre and compares its two basis vectors.

The proxy is the larger of:

- local scale anisotropy;
- local non-orthogonality.

A fronto-parallel affine mapping therefore approaches zero. The score is bounded to `[0, 1]`.

This is a projective-geometry guidance proxy only. It is not an estimate of camera pitch/roll/yaw in degrees and must not be exposed as physical pose truth.

### Perspective-scale ratio

The evaluator inspects the homogeneous denominator over all four source-frame corners. The ratio between its maximum and minimum absolute value is scale-invariant and equals `1` for an affine mapping.

A growing ratio indicates stronger projective scale variation across the image. A sign change or projective pole within the source-frame boundary fails closed with `CaptureAlignmentError` rather than producing a plausible-looking result.

## Policy

`CaptureAlignmentPolicy` defaults:

- camera-tilt proxy: WARN `> 0.25`, REJECT `> 0.50`;
- perspective scale ratio: WARN `> 1.35`, REJECT `> 2.00`.

These are deterministic software defaults for Guided Capture behavior, not physically calibrated phone-camera limits. Real-device/dataset calibration remains future work.

Each check can be disabled independently for controlled tests or future product policy composition.

## Actions

Machine-readable actions:

- `CONTINUE_CAPTURE_WORKFLOW`;
- `REALIGN_CAMERA_PERPENDICULAR`;
- `REDUCE_PERSPECTIVE_DISTORTION`.

`RussianCaptureAlignmentGuidanceAdapter` converts findings into actionable operator guidance without embedding user-facing text in the decision logic.

## Fail-closed and lineage behavior

Alignment evaluation requires:

1. an active clean-reference frame for the requested view;
2. calibration attached to that exact active clean-reference frame;
3. a finite non-degenerate homography over the source frame.

A calibration belonging to a superseded clean reference is not reused after recapture. The view must be calibrated again before alignment guidance can be produced for the new active attempt.

## State / contract boundary

Pass 19 is read-only.

It does not:

- mutate `CaptureSession`;
- create or replace artifacts;
- mutate clean-reference lineage;
- persist alignment verdicts as measurement evidence;
- create calibration truth;
- create physical camera-pose truth;
- create `PhysicalMeasurement` values;
- modify `CapturePackage v1` or any shared contract/fixture.

The same session serialisation and canonical `CapturePackage` are preserved before and after evaluation.

## Tests

`tests/test_alignment.py` covers:

1. fronto-parallel affine mapping -> accepted alignment;
2. strong anisotropy -> camera-tilt risk;
3. strong projective scale variation -> perspective rejection;
4. moderate projective variation -> actionable warning;
5. missing active calibration fails closed;
6. stale calibration is ignored after clean-reference recapture;
7. projective denominator sign change fails closed;
8. repeated evaluation is deterministic, read-only and canonical-neutral.

Required branch evidence before freeze:

- `Chat 1 / Capture` — success;
- `Contracts / canonical fixtures` — success;
- `Integration / Chat 1 -> Chat 2` — success.
