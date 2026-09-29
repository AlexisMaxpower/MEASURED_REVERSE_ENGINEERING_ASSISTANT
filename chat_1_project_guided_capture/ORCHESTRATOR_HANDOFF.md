# ORCHESTRATOR HANDOFF — Chat 1

**Pass:** 1  
**Directive closed:** `OD-2026-09-29-001`  
**Date:** 2026-09-29  
**From:** Chat 1 — Project & Guided Capture  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Contract baseline:** `mrea.contracts.v1`

## Delivered

Pass 1 delivers a working Project/Capture baseline through canonical Capture output:

```text
Project + PartContext
→ CapturePlan
→ CaptureSession
→ clean reference
→ manual measurement frames
→ ChArUco calibration
→ canonical ProjectContract v1
→ canonical CapturePackage v1
→ JSON Schema validation
```

## Canonical inputs used

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/project_v1.json`;
- `tests/fixtures/contracts/capture_package_v1.json`.

No shared contract or canonical fixture was copied or modified by Chat 1.

## Implementation delivered

### Project/Capture domain

- stable `project_id` and `part_id`;
- deterministic legacy `part_id` backfill;
- Project create/recovery/archive;
- deterministic CapturePlan;
- persistent CaptureSession;
- offline-first JSON repositories.

### Manual capture

- camera metadata;
- immutable clean-reference / measurement-frame separation;
- content-addressed local artifact store;
- SHA-256 integrity verification;
- measurement-frame-before-clean-reference rejection;
- required-view completion behavior.

### Canonical boundary

- `CanonicalContractBuilder.project_contract()`;
- `CanonicalContractBuilder.capture_package()`;
- canonical `ArtifactReference` mapping;
- canonical `MeasurementCaptureFrame` mapping;
- deterministic opaque `capture_package_id` / `view_id`;
- UTC/RFC3339 wire timestamps;
- stable project/part linkage;
- canonical FRONT schema validation.

### Calibration baseline

- `MeasurementMatProfile`;
- `CalibrationResult` persistence;
- `CalibrationDetector` abstraction;
- `OpenCvCharucoCalibrationDetector`;
- ChArUco marker/corner detection;
- RANSAC homography `IMAGE_PX -> MAT_XY_MM`;
- calibration provenance tied to clean reference;
- objective marker/corner/RMSE evidence;
- canonical non-null `CapturePackage.views[].calibration`.

## Verification

Latest full local Chat 1 regression:

```text
13 passed in 1.07s
```

Verified by tests:

1. Project create/recovery and validation;
2. stable `part_id`, including legacy backfill;
3. CapturePlan ordering/deduplication;
4. CaptureSession persistence;
5. artifact SHA-256 round-trip;
6. clean/measurement evidence separation;
7. required FRONT completion;
8. canonical ProjectContract schema validation;
9. canonical FRONT CapturePackage schema validation;
10. deterministic canonical serialization;
11. canonical measurement-frame serialization;
12. synthetic ChArUco calibration;
13. canonical CapturePackage with non-null calibration validates against shared schema.

Synthetic calibration fixture result:

- 5x7 ChArUco board;
- 24 detected ChArUco corners;
- marker detection succeeds;
- 9-value homography;
- reprojection RMSE `< 0.001 mm` on synthetic input.

## Directive acceptance target

`OD-2026-09-29-001` requested a schema-valid canonical CapturePackage for one FRONT view.

**Chat 1 implementation status: SATISFIED.**

The same boundary now also supports non-null canonical calibration for FRONT.

## Current limitations

Not yet verified/implemented:

- perspective-normalized derived image artifact;
- clean-reference → rectified-artifact provenance;
- synthetic perspective warp regression;
- physical printed Measurement Mat accuracy;
- camera lens distortion/intrinsics policy;
- Guided Quality warnings;
- native/mobile camera runtime;
- voice-trigger capture;
- GitHub Actions CI.

`calibration.quality` remains `null` because no canonical scalar quality formula has been approved. Objective evidence is retained instead of inventing a score.

## Acceptance requested from Chat 6

Please verify:

1. `OD-2026-09-29-001` is accepted/closed for Chat 1;
2. canonical Project/Capture serialization is acceptable;
3. ChArUco calibration mapping to canonical `views[].calibration` is acceptable;
4. Pass 1 may be treated as the integration baseline for Chat 1;
5. update `ORCHESTRATION_STATE.md` / `SLICE_STATUS.md` as appropriate;
6. issue the next `ORCHESTRATOR_DIRECTIVE.md` revision before Pass 2 if cross-slice priorities changed.

## Proposed next Chat 1 target

Unless Chat 6 redirects the slice, next implementation target is perspective normalization:

```text
clean reference
+ stored IMAGE_PX → MAT_XY_MM homography
→ deterministic rectified raster
→ immutable derived artifact
→ explicit source → derived provenance
→ synthetic perspective-distortion regression
```
