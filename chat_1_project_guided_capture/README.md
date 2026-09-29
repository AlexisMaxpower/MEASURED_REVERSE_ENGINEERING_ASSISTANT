# Chat 1 — Project & Guided Capture

Эта директория является изолированной рабочей областью Chat 1 проекта MREA.

## Ownership

Chat 1 отвечает за вертикальный слайс `Project & Guided Capture`: создание проекта, CapturePlan, camera workflow, guided capture, Measurement Mat detection, calibration, clean reference frame, measurement-frame capture, voice capture trigger, image-quality analysis и формирование `CapturePackage`.

Chat 1 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Структура

```text
chat_1_project_guided_capture/
├─ MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md
├─ pyproject.toml
├─ src/
│  └─ mrea_capture/
│     ├─ __init__.py
│     ├─ artifacts.py
│     ├─ models.py
│     ├─ repositories.py
│     └─ services.py
├─ tests/
│  ├─ test_project_service.py
│  ├─ test_capture_plan.py
│  └─ test_manual_capture.py
└─ docs/
   ├─ CHAT_1_ROLE.md
   ├─ BUILD_REUSE_CHECK_PHASE1.md
   ├─ BUILD_REUSE_CHECK_PHASE2.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE1_2026-09-29.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE2_2026-09-29.md
   └─ IMPLEMENTATION_STATE.md
```

## Реализовано

### R1 Phase 1 — Project/Capture domain

- `Project` + `PartContext`;
- project creation/recovery;
- replaceable `ProjectRepository`;
- local offline-first `JsonProjectRepository`;
- deterministic `CapturePlan`;
- CaptureSession initialization.

### R1 Phase 2 — Manual Capture Baseline

- `CameraMetadata`;
- `FrameRecord` + `FrameKind`;
- distinct `CLEAN_REFERENCE` / `MEASUREMENT` frames;
- replaceable `ArtifactStore`;
- content-addressed filesystem artifacts with SHA-256 verification;
- `JsonCaptureSessionRepository`;
- clean reference capture;
- manual measurement-frame capture;
- prohibition of measurement frame before clean reference;
- FRONT view acceptance/completion;
- optional `OPTIONAL_3Q` does not block required-view completion.

Последняя локальная проверка:

```text
10 passed in 0.06s
```

## Следующий этап

R1 Phase 3 — Calibration Baseline:

- Measurement Mat representation/versioning;
- marker detection adapter boundary;
- calibration result model;
- perspective normalization interface;
- registration metadata;
- fixtures/tests for good/partial/missing marker cases.

Shared contracts (`ProjectContract`, `CapturePackage`, `MeasurementCaptureFrame`, `ArtifactReference`) всё ещё ожидают canonical schemas/fixtures от Integrator. Chat 1 не определяет их самостоятельно.
