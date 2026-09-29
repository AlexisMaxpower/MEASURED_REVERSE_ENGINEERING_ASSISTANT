# Chat 1 — Implementation State

**Date:** 2026-09-29  
**Role:** Chat 1 — Project & Guided Capture  
**Current product pass:** 2  
**Current coordination pass:** 3 (CI / acceptance closure only)  
**Directive:** `OD-2026-09-29-002`  
**Working branch:** `chat-1/pass-2`  
**Review PR:** `#16`

## Source-of-truth order

1. current repository state for the active pass branch;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + Chat 6 orchestration state/directive;
5. Chat 1 local docs.

Chat 1 does not modify shared contracts or canonical fixtures.

## Accepted baseline — Pass 1

Chat 6 accepted:

- Project/Capture domain;
- manual capture baseline;
- stable project/part linkage;
- canonical `ProjectContract v1` / `CapturePackage v1` adapters;
- ChArUco calibration baseline;
- schema-valid FRONT CapturePackage with calibration.

## Pass 2 implemented

### Stable calibration provenance

- `CalibrationResult.calibration_id` added as an internal identifier;
- legacy calibration records without the field receive deterministic UUIDv5 backfill from source frame + mat identity.

### Perspective normalization

Added:

- `RectifiedReferenceRecord`;
- `CaptureSession.rectified_references` persistence;
- `PerspectiveNormalizer` protocol;
- `OpenCvPerspectiveNormalizer`;
- `RectificationService`;
- explicit `RectificationError` failures.

Flow:

```text
clean reference artifact
+ stored calibration homography
+ MeasurementMatProfile
+ pixels_per_mm
-> deterministic MAT-space raster
-> new content-addressed artifact
-> RectifiedReferenceRecord
```

Invariants:

- source clean artifact is never overwritten;
- derived artifact has independent artifact ID/SHA;
- source frame ID is preserved in provenance;
- exact calibration ID and mat ID are preserved;
- one rectified reference per view in current baseline;
- singular/non-finite homographies fail explicitly;
- existing calibration is reused; no second calibration representation exists.

### Canonical boundary

No shared contract change.

`CapturePackage v1` has no rectified-artifact property. Rectification therefore stays internal while the canonical package continues to expose original clean reference + calibration homography. Canonical serialization before and after internal rectification remains unchanged.

## Verification

### Local

Latest full local Chat 1 regression on exact branch-equivalent bytes:

```text
16 passed in 1.13s
```

Pass 2 synthetic perspective test verifies:

- known perspective distortion of a 5x7 ChArUco board;
- calibration of the distorted reference;
- deterministic repeated encoded output;
- preserved source bytes;
- distinct derived artifact identity/hash;
- source/calibration/mat provenance;
- 1000x1400 raster at 10 px/mm for 100x140 mm mat geometry;
- mean absolute image error `< 8` against known canonical raster;
- canonical CapturePackage remains schema-valid and unchanged;
- singular homography explicit failure;
- stable legacy calibration-ID backfill.

### GitHub Actions / PR integration

PR `#16` (`chat-1/pass-2 -> main`) has successful MREA CI evidence.

Successful workflow run:

- run ID: `36610773229`;
- run number: `28`;
- conclusion: `success`;
- branch/PR head checked by the run: `b1cabe7627bba984319ac40c942b1d13b424cce9`.

Successful executable jobs:

- Contracts / canonical fixtures;
- Chat 1 / Capture;
- Chat 2 / Measurement;
- Chat 3 / Geometry;
- Chat 4 / Generic CAD gate;
- Chat 5 / Lifecycle;
- Integration / Chat 2 -> Chat 3.

`Integration / Chat 4 -> Chat 5` was skipped by workflow condition because this is a Chat 1 PR; this is expected, not a failure.

Earlier red runs on the evolving branch are superseded by successful run `36610773229`.

## Current limitations

- no real printed-mat accuracy validation;
- no camera lens-distortion/intrinsics compensation;
- deterministic raster policy is pinned to current OpenCV behavior, not promised across arbitrary future versions;
- rectified artifact is internal until/if Chat 6 creates a canonical exposure path;
- no rectified-reference replacement/versioning policy;
- no Guided Quality implementation yet;
- native/mobile runtime is not verified.

## Integration readiness

Ready for Chat 6 Pass 2 acceptance review:

- deterministic perspective normalization;
- immutable derived artifact;
- explicit source/calibration provenance;
- source evidence preservation;
- canonical backward compatibility;
- full local regression passing;
- PR-level GitHub Actions green.

No new product functionality is started in coordination Pass 3 because `OD-003` has not yet been issued. Next product work must follow the next Chat 6 directive after Pass 2 acceptance.
