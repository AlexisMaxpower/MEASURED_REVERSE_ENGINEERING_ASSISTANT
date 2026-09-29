# Chat 1 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 1 — Project & Guided Capture  
**Orchestrator directive:** `OD-2026-09-29-001`

---

## Source-of-truth status

Chat 6 published R0 contracts/fixtures. Current hierarchy used by Chat 1:

1. current repository state on `main`;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + orchestration addendum;
5. Chat 1 local documentation.

Chat 1 does not modify shared contracts.

---

## Implemented

### R1 Phase 1 — Project/Capture domain

- `PartContext`;
- `Project` / `ProjectStatus`;
- stable `part_id`;
- deterministic backward-compatible `part_id` backfill for legacy Project JSON;
- `CaptureViewType` / `CaptureViewStatus`;
- `CapturePlanItem` / `CapturePlan`;
- deterministic CapturePlan construction;
- default `FRONT` baseline;
- `ProjectRepository` protocol + `JsonProjectRepository`;
- `ProjectService` create/get/archive;
- strict validation and timezone-aware timestamps.

### R1 Phase 2 — Manual Capture Baseline

- `CameraMetadata`;
- internal `ArtifactRecord`;
- clean-reference and measurement frame separation;
- persisted `CaptureSession.frames`;
- `CaptureSessionRepository` protocol + JSON adapter;
- content-addressed `FileSystemArtifactStore`;
- SHA-256 integrity check;
- capture/accept workflow;
- required-view completion;
- measurement frame forbidden before clean reference.

### Orchestrator canonical integration gate

- consumed `ORCHESTRATOR_DIRECTIVE.md`;
- consumed canonical `mrea.contracts.v1` schema/policies;
- `CanonicalContractBuilder.project_contract()`;
- `CanonicalContractBuilder.capture_package()`;
- canonical `ArtifactReference` mapping;
- canonical `MeasurementCaptureFrame` mapping;
- deterministic opaque `capture_package_id` and `view_id`;
- UTC/RFC3339 wire timestamps;
- schema validation against Integrator-owned JSON Schema;
- canonical FRONT package contains clean reference + measurement frames;
- current calibration field is explicit `null` until Phase 3.

---

## Verification

Latest full local Chat 1 regression run:

```text
12 passed in 0.89s
```

Verified:

1. project create/restore;
2. stable `part_id` across persistence and legacy backfill;
3. CapturePlan behavior;
4. CaptureSession persistence;
5. artifact SHA-256 round-trip;
6. clean/measurement frame invariants;
7. required FRONT completion;
8. generated `ProjectContract v1` validates against canonical schema;
9. generated one-view FRONT `CapturePackage v1` validates against canonical schema;
10. Project/Capture `project_id` + `part_id` continuity;
11. deterministic repeated canonical serialization;
12. canonical measurement frame serialization.

Environment:

- Pydantic `2.13.4`;
- pytest `9.0.2`;
- jsonschema `4.26.0`.

No GitHub Actions CI has been run yet.

---

## Orchestrator directive status

`OD-2026-09-29-001` requested:

- keep internal models;
- add outward adapters for `ProjectContract v1` and `CapturePackage v1`;
- reconcile stable `part_id`;
- preserve opaque wire IDs;
- produce schema-valid canonical FRONT CapturePackage;
- do not modify `core/contracts` or measurement semantics.

Status: **implemented locally in Chat 1 ownership and verified by tests**.

No shared contract change request is required.

---

## Next implementation target

### R1 Phase 3 — Calibration Baseline

1. Build/Reuse check for OpenCV ArUco/ChArUco;
2. Measurement Mat identity/version model;
3. calibration detector interface;
4. marker visibility result;
5. homography/calibration result;
6. perspective normalization;
7. original → rectified artifact provenance;
8. populate canonical `CapturePackage.views[].calibration` instead of `null`;
9. synthetic fixture tests before real-camera dataset.

---

## Known limitations

- artifact URI currently uses logical `mrea://artifact/{artifact_id}`; shared Artifact Registry resolver is not yet implemented;
- camera bytes enter service already captured; native camera adapter is not implemented;
- image MIME/extension is not decoded/verified;
- concurrent JSON writers are unsupported;
- clean reference recapture/replacement is not implemented;
- calibration/CV/guided quality are not implemented;
- mobile filesystem behavior is unverified;
- CI is absent.

---

## Integration readiness

Ready for Chat 6 integration review:

- Project create/recovery with stable `part_id`;
- CapturePlan/CaptureSession;
- manual capture artifacts;
- canonical `ProjectContract v1` adapter;
- canonical one-view FRONT `CapturePackage v1` builder;
- canonical contract tests;
- 12 passing Chat 1 tests.

Not yet ready:

- non-null calibration;
- guided image quality;
- native/mobile camera;
- voice-trigger capture;
- end-to-end CI.
