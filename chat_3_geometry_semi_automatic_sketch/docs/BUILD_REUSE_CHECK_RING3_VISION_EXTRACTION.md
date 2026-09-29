# Build / Reuse Check — Ring 3 Vision Geometry Extraction

**Date:** 2026-09-29  
**Directive:** `OD-2026-09-29-003`  
**Branch:** `chat-3/pass-3`

## Goal

Add the first real semi-automatic image → geometry candidate boundary without replacing verified physical measurements or inventing hidden geometry.

## Reuse decision

Ring 3 uses `opencv-python-headless` instead of implementing generic computer-vision algorithms locally.

Reused OpenCV capabilities:

- image decoding;
- Otsu thresholding;
- contour hierarchy;
- polygon approximation;
- contour area/perimeter/circularity;
- connected components;
- minimum enclosing circle.

Reused existing MREA code:

- Ring 2 homography application;
- `GeometryPipeline`;
- measurement binding and conflict detection;
- `SketchPackageBuilder`;
- canonical unresolved-item shape.

## New dependency

Runtime dependency:

```text
opencv-python-headless >=4.10,<5
```

Headless package is used because this slice performs processing only and does not require GUI bindings.

## MREA-specific code retained locally

Custom code is limited to product rules that OpenCV cannot own:

- deterministic candidate IDs/order;
- truthful `VISION_DETECTED` provenance;
- confidence projection;
- feature naming for reliable FRONT quadrilateral edges/holes;
- conversion through calibrated homography;
- verified-measurement binding without rewriting measurement values;
- fail-closed ambiguity handling;
- canonical `unresolved` projection;
- restriction of CIRCLE/ARC promotion to circle-preserving similarity transforms.

## Why CIRCLE / ARC require a similarity transform

A general projective homography maps circles to conics. Emitting a `CIRCLE` or `ARC` after an arbitrary projective transform would silently fabricate geometry not supported by the image/calibration pair.

Therefore:

- LINE candidates may be transformed projectively;
- CIRCLE/ARC candidates are promoted only when the 2×2 affine part is orthogonal with equal scale and no projective denominator terms;
- otherwise an explicit unresolved issue is emitted.

## Failure policy

The extractor does not guess when evidence is insufficient.

Explicit unresolved cases include:

- no usable reference contour;
- multiple similarly significant outer contours;
- unsupported non-quadrilateral outer profile;
- non-circular inner contour;
- circle/arc under non-circle-preserving calibration;
- open component that does not fit a circular arc reliably;
- ambiguous arc coverage.

## Fixture strategy

Stable textual PBM images are committed in Git so exact bytes can be reviewed and hashed. Golden outputs are committed separately.

This avoids generated-at-test-time images that could hide the actual visual evidence used by the detector.

## Lock-in / fallback

Lock-in is low:

- OpenCV stays behind `ImageGeometryExtractor`;
- downstream MREA models remain library-independent;
- a future detector can replace OpenCV without changing `GeometryPipeline` or canonical `SketchPackage v1`.

## Decision

**REUSE OpenCV for generic vision operations; BUILD only the MREA-specific candidate/provenance/measurement boundary.**
