# BUILD / REUSE CHECK — R1 Phase 3 Perspective Normalization

**Pass:** 2  
**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-1/pass-2`  
**Date:** 2026-09-29

## Problem

Chat 1 must convert an immutable clean-reference image into a deterministic raster aligned to the existing `IMAGE_PX -> MAT_XY_MM` calibration while preserving the original evidence artifact.

## Existing reusable implementation

YES. OpenCV already provides the generic image-warp primitives required for this operation:

- `cv2.warpPerspective`;
- `cv2.imdecode`;
- `cv2.imencode`;
- NumPy matrix/rank validation.

## Decision

REUSE OpenCV for pixel resampling and image encoding. Do not implement a custom perspective rasterizer.

## MREA-owned logic

MREA implements only product/domain semantics:

- deterministic MAT raster size derived from `MeasurementMatProfile` and `pixels_per_mm`;
- validation that the stored calibration belongs to the clean source frame and selected mat;
- explicit rejection of singular/non-finite homographies;
- immutable derived artifact creation through the existing `ArtifactStore`;
- persisted `RectifiedReferenceRecord`;
- provenance linking derived artifact to `source_frame_id`, `calibration_id`, and `mat_id`;
- one rectified reference per view in the current baseline;
- canonical-boundary compatibility policy.

## Canonical contract policy

`CapturePackage v1` has no field for a rectified artifact and uses `additionalProperties: false` at the view level.

Therefore Pass 2 does **not** extend or mutate the shared contract. The canonical package continues to expose:

- original `clean_reference_frame`;
- measurement frames;
- calibration/homography.

The derived rectified artifact is an internal Chat 1 artifact. This preserves backward compatibility and Chat 6 ownership of shared contracts.

## Determinism policy

For a fixed input image, homography, mat profile, `pixels_per_mm`, and OpenCV implementation:

- output dimensions are deterministic;
- interpolation is fixed to `INTER_LINEAR`;
- border mode/value is fixed;
- PNG compression is fixed;
- encoded bytes are tested for equality across repeated normalization calls.

## Lock-in risk

LOW/MEDIUM. OpenCV-specific calls are isolated behind `PerspectiveNormalizer`. `RectificationService` depends only on the protocol and internal domain records.

## Fallback

A native/mobile warp implementation can replace `OpenCvPerspectiveNormalizer` without changing CaptureSession semantics or canonical contracts.
