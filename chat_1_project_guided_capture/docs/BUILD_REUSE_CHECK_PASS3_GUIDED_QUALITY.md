# BUILD / REUSE CHECK — Chat 1 Pass 3 Guided Capture Quality

**Date:** 2026-09-29  
**Directive:** `OD-2026-09-29-003`

## Problem

Guided Capture needs fast, deterministic diagnostics for whether an image is usable before downstream measurement/geometry work begins.

Required signals:

- blur/focus;
- under/over exposure and clipping;
- glare/highlight risk;
- framing / working-area proxy;
- calibration-marker visibility when calibration evidence already exists;
- explicit `ACCEPT` / `WARN` / `REJECT` result with machine-readable reasons.

These signals are diagnostics only. They must never become metric truth or silently modify physical measurement values.

## Existing reusable components

YES.

OpenCV already provides the low-level image primitives needed for this baseline:

- image decode;
- grayscale/HSV conversion;
- Laplacian operator;
- Canny edge detection;
- connected-component statistics;
- deterministic NumPy/OpenCV array operations.

The existing Chat 1 calibration pipeline already stores ChArUco detection evidence that can be reused for marker-visibility quality.

## What is reused

- `cv2.imdecode`;
- `cv2.cvtColor`;
- `cv2.Laplacian` variance as a focus/blur proxy;
- thresholded pixel fractions for exposure clipping;
- HSV + connected components as a conservative glare/highlight proxy;
- `cv2.Canny` edge density and border-edge ratio as framing/scene-detail proxies;
- existing `CalibrationResult.detected_charuco_corner_count` and `MeasurementMatProfile` for marker visibility.

No new third-party dependency is required beyond the existing Pass 1/2 OpenCV + NumPy vision baseline.

## What MREA implements

- `CaptureQualityPolicy` with explicit versioned thresholds;
- `CaptureQualityMetrics`;
- `CaptureQualityFinding`;
- `CaptureQualityResult`;
- `CaptureQualityVerdict`: `ACCEPT`, `WARN`, `REJECT`;
- machine-readable `QualityReasonCode` values;
- deterministic rule aggregation;
- `CaptureQualityService` persistence against immutable clean-reference frames;
- explicit source frame / calibration / mat provenance;
- Russian presentation adapter for actionable guidance;
- deterministic generated fixtures and regression tests.

## Why these are proxies

Image-quality metrics are content- and camera-dependent. For example:

- Laplacian variance is not an optical MTF measurement;
- histogram clipping does not prove physical illumination quality;
- highlight masks do not prove specular reflection geometry;
- border-edge ratio does not segment the physical part;
- marker visibility is evidence completeness, not dimensional accuracy.

Therefore the baseline reports them only as capture diagnostics.

## Policy baseline

Default thresholds are intentionally explicit and versioned as:

`chat1.capture-quality.v1`

They are suitable for deterministic software behavior and synthetic regression, not yet validated as production thresholds across real phone cameras, lenses and lighting environments.

Real-device validation may tune thresholds in a future policy revision without changing canonical shared contracts.

## Framing decision

Pass 3 does not introduce object segmentation. Framing uses two conservative image-space proxies:

- total edge density — detects nearly empty / unusable scenes;
- fraction of detected edges inside an outer border band — warns when significant scene structure reaches the frame edge.

This avoids inventing object geometry ownership inside Chat 1.

## Glare decision

The glare proxy considers small/medium connected high-value, low-saturation regions. Very large bright regions are excluded from the glare proxy because a white Measurement Mat or uniformly overexposed image would otherwise be misclassified as a collection of specular highlights; exposure rules handle broad clipping separately.

## Lock-in risk

LOW/MEDIUM.

OpenCV-specific operations are isolated in `OpenCvCaptureQualityAnalyzer`. Domain result models and `CaptureQualityService` do not expose OpenCV/NumPy objects.

## Fallback

A native mobile analyzer, GPU implementation or another CV library can implement the same `CaptureQualityAnalyzer` protocol while preserving the internal result model and orchestration behavior.
