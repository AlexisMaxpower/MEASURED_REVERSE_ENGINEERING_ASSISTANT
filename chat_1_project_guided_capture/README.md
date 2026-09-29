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
│     ├─ models.py
│     ├─ repositories.py
│     └─ services.py
├─ tests/
│  ├─ test_project_service.py
│  └─ test_capture_plan.py
└─ docs/
   ├─ CHAT_1_ROLE.md
   ├─ BUILD_REUSE_CHECK_PHASE1.md
   ├─ IMPLEMENTATION_REPORT_R1_PHASE1_2026-09-29.md
   └─ IMPLEMENTATION_STATE.md
```

## Реализовано

R1 Phase 1:

- `Project` + `PartContext`;
- project creation/recovery;
- replaceable `ProjectRepository` interface;
- local offline-first `JsonProjectRepository`;
- supported capture view enum;
- deterministic `CapturePlan`;
- `CaptureSession` state initialization;
- strict validation;
- 6 unit tests.

Локальная проверка Phase 1:

```text
6 passed in 0.07s
```

## Следующий этап

R1 Phase 2 — Manual Capture Baseline:

- frame ingestion abstraction;
- camera metadata;
- local artifact storage;
- clean reference frame;
- manual measurement frame;
- CaptureSession transitions tied to real frame artifacts.

Shared contracts (`ProjectContract`, `CapturePackage`, `MeasurementCaptureFrame`, `ArtifactReference`) всё ещё ожидают canonical schemas/fixtures от Integrator. Chat 1 не определяет их самостоятельно.
