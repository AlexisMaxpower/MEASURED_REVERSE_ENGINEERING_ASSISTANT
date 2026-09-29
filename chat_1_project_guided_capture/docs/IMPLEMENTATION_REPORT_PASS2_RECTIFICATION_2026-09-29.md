# IMPLEMENTATION REPORT — Chat 1 / Pass 2 Perspective Normalization

**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-1/pass-2`  
**Date:** 2026-09-29

## Delivered

Implemented the Pass 2 perspective-normalization gate:

```text
immutable clean reference
+ stored IMAGE_PX -> MAT_XY_MM homography
-> deterministic rectified raster
-> immutable derived ArtifactRecord
-> RectifiedReferenceRecord
-> source/calibration provenance
```

## Domain changes

- added deterministic internal `calibration_id` to `CalibrationResult`;
- old calibration JSON without `calibration_id` receives stable UUIDv5 backfill from `source_frame_id + mat_id`;
- added `RectifiedReferenceRecord`;
- `CaptureSession` persists `rectified_references` and rejects duplicates per view.

## Infrastructure/application changes

Added `rectification.py`:

- `PerspectiveNormalizer` protocol;
- `OpenCvPerspectiveNormalizer`;
- `RectificationService`;
- `RectificationError`;
- `RectifiedRaster`.

The normalizer:

- reuses the stored calibration homography;
- validates finite/full-rank 3x3 transform;
- derives raster dimensions from mat dimensions and configured pixels/mm;
- uses a fixed OpenCV interpolation/border/PNG encoding policy;
- never overwrites the source image.

The service:

- requires exactly one clean reference and one calibration for the view;
- verifies calibration provenance;
- saves rectified bytes as a new immutable content-addressed artifact;
- persists source frame, calibration, mat and raster metadata.

## Canonical compatibility

No shared schema or fixture was modified.

`CapturePackage v1` has no rectified-artifact field. The derived artifact remains internal and the canonical package stays byte-for-byte equivalent before/after rectification for the same session calibration state.

## Tests

Full local Chat 1 regression after Pass 2 implementation:

```text
16 passed in 1.17s
```

New regression coverage proves:

1. synthetic 5x7 ChArUco reference is warped by a known perspective transform;
2. existing calibration recovers `IMAGE_PX -> MAT_XY_MM` homography;
3. repeated normalization produces identical encoded PNG bytes;
4. derived artifact has a distinct artifact identity/hash;
5. original clean-reference bytes remain retrievable and unchanged;
6. provenance contains exact source frame + calibration + mat identifiers;
7. output raster is 1000x1400 at 10 px/mm for the 100x140 mm mat;
8. normalized raster matches known canonical geometry with mean absolute pixel error `< 8`;
9. canonical CapturePackage is unchanged by internal rectification and remains schema-valid;
10. singular homography fails explicitly;
11. legacy calibration without `calibration_id` gets a stable deterministic identity.

## Limitations

- physical printed Measurement Mat accuracy remains unverified;
- camera lens distortion/intrinsics are not compensated;
- interpolation determinism is guaranteed within the fixed implementation/runtime baseline, not across arbitrary future OpenCV versions;
- derived artifact is internal because canonical v1 has no field for it;
- one rectified reference per view; explicit replacement/versioning policy is not implemented;
- mobile/native runtime and CI are not yet verified.

## Acceptance target status

`OD-2026-09-29-002` implementation target is satisfied locally. Final implementation SHA and acceptance request are recorded in `ORCHESTRATOR_HANDOFF.md` after repository write-back.
