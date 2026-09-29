# Chat 1 — Project & Guided Capture

Эта директория является изолированной рабочей областью Chat 1 проекта MREA.

## Ownership

Chat 1 отвечает за vertical slice `Project & Guided Capture`: project creation, part initial context, CapturePlan, camera/capture workflow, Guided Capture, Measurement Mat detection, calibration, clean reference frame, measurement-frame capture, voice capture trigger, image-quality analysis и формирование canonical `CapturePackage`.

Chat 1 не владеет shared contracts и не изменяет `core/contracts/` или `tests/fixtures/contracts/` без решения Chat 6 — Orchestrator / Repository Integrator.

## Source of truth

1. current repository state on `main`;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT + orchestrator directives/state;
5. Chat 1 local documentation.

Current orchestrator directive: `OD-2026-09-29-001`.

## Current structure

```text
chat_1_project_guided_capture/
├─ MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md
├─ ORCHESTRATOR_DIRECTIVE.md
├─ ORCHESTRATOR_HANDOFF.md
├─ README.md
├─ pyproject.toml
├─ src/
│  └─ mrea_capture/
│     ├─ __init__.py
│     ├─ artifacts.py
│     ├─ calibration.py
│     ├─ contracts.py
│     ├─ models.py
│     ├─ repositories.py
│     └─ services.py
├─ tests/
│  ├─ test_project_service.py
│  ├─ test_capture_plan.py
│  ├─ test_manual_capture.py
│  ├─ test_canonical_contracts.py
│  └─ test_calibration.py
└─ docs/
   ├─ CHAT_1_ROLE.md
   ├─ BUILD_REUSE_CHECK_PHASE1.md
   ├─ BUILD_REUSE_CHECK_PHASE2.md
   ├─ BUILD_REUSE_CHECK_PHASE3_CALIBRATION.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE1_2026-09-29.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE2_2026-09-29.md
   ├─ IMPLEMENTATION_REPORT_ORCHESTRATOR_GATE_2026-09-29.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE3_CALIBRATION_2026-09-29.md
   └─ IMPLEMENTATION_STATE.md
```

## Implemented in Pass 1

### R1 Phase 1 — Project/Capture domain

- `Project` + `PartContext`;
- stable `project_id` and `part_id`;
- deterministic legacy `part_id` backfill;
- project create/recovery/archive;
- replaceable repository abstraction;
- offline-first JSON persistence;
- deterministic `CapturePlan` and CaptureSession initialization.

### R1 Phase 2 — Manual Capture

- `CameraMetadata`;
- distinct clean-reference and measurement frames;
- content-addressed filesystem artifacts with SHA-256 verification;
- persistent CaptureSession;
- clean reference capture;
- manual measurement-frame capture;
- measurement frame forbidden before clean reference;
- required-view acceptance/completion.

### Orchestrator canonical gate

- outward adapter to canonical `ProjectContract v1`;
- canonical `CapturePackage v1` builder;
- canonical `ArtifactReference` and `MeasurementCaptureFrame` mapping;
- deterministic opaque package/view IDs;
- schema validation against Integrator-owned `mrea.contracts.v1`;
- one-view FRONT package acceptance target from `OD-2026-09-29-001` satisfied.

### R1 Phase 3 — Calibration baseline

- `MeasurementMatProfile`;
- ChArUco detection through OpenCV;
- RANSAC homography `IMAGE_PX -> MAT_XY_MM`;
- calibration persistence and clean-reference provenance;
- marker/corner evidence + reprojection RMSE;
- non-null canonical `views[].calibration`;
- synthetic ChArUco integration test.

Current canonical `calibration.quality` remains `null` until an explicit quality policy is approved.

## Verification

Latest full local Chat 1 regression:

```text
13 passed in 1.07s
```

Verified:

- Project create/recovery and stable IDs;
- manual capture invariants;
- canonical Project/Capture schema validation;
- deterministic canonical serialization;
- synthetic 5x7 ChArUco detection with 24 corners;
- 9-value homography;
- reprojection RMSE `< 0.001 mm` on synthetic fixture;
- canonical CapturePackage with calibration validates against shared schema.

This is local verification; GitHub Actions CI has not yet been run.

## Remaining work

- perspective-normalized derived artifact and source → derived provenance;
- deterministic warp test with synthetic perspective distortion;
- physical printed Measurement Mat validation;
- lens distortion / camera intrinsics strategy;
- Guided Quality checks;
- native/mobile camera integration;
- voice-trigger capture;
- API/CI.

See `docs/IMPLEMENTATION_STATE.md` for the detailed current state and `ORCHESTRATOR_HANDOFF.md` for the integration handoff to Chat 6.
