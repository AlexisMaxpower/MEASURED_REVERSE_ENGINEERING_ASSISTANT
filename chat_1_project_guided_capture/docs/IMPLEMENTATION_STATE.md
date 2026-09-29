# Chat 1 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 1 — Project & Guided Capture

---

## Current repository state

Repository содержит пять изолированных chat workspaces. Root-level R0 architecture/shared-contract structure от Integrator пока отсутствует.

Chat 1 изменяет только `chat_1_project_guided_capture/`.

---

## Implemented

### R1 Phase 1 — Project/Capture domain

- `PartContext`;
- `Project` / `ProjectStatus`;
- `CaptureViewType` / `CaptureViewStatus`;
- `CapturePlanItem` / `CapturePlan`;
- deterministic CapturePlan construction;
- default `FRONT` baseline;
- `ProjectRepository` protocol;
- `JsonProjectRepository`;
- `ProjectService.create_project()`;
- `ProjectService.get_project()`;
- `ProjectService.archive_project()`;
- explicit `ProjectNotFoundError`;
- strict Pydantic validation;
- timezone-aware Project timestamps.

### R1 Phase 2 — Manual Capture Baseline

- `CameraMetadata`;
- internal `ArtifactRecord`;
- `FrameKind.CLEAN_REFERENCE`;
- `FrameKind.MEASUREMENT`;
- `FrameRecord`;
- `CaptureViewProgress.required`;
- persisted `CaptureSession.frames`;
- `CaptureSessionRepository` protocol;
- `JsonCaptureSessionRepository`;
- `ArtifactStore` protocol;
- content-addressed `FileSystemArtifactStore`;
- SHA-256 integrity check при чтении artifact;
- `CaptureSessionService.start()`;
- `capture_clean_reference()`;
- `capture_measurement_frame()`;
- `accept_view()`;
- completion, когда все required views имеют `ACCEPTED`;
- optional `OPTIONAL_3Q` не блокирует completion;
- measurement frame запрещён до clean reference того же view;
- view запрещено принимать без clean reference;
- clean reference и measurement frames остаются отдельными evidence artifacts.

---

## Verification

Последний полный локальный Chat 1 run:

```text
10 passed in 0.06s
```

Проверено тестами:

1. project create + restore from disk;
2. unknown project explicit error;
3. blank project name validation;
4. default FRONT CapturePlan;
5. explicit plan ordering + duplicate removal;
6. CaptureSession persistence after start;
7. artifact bytes round-trip + SHA-256 metadata;
8. measurement frame rejected before clean reference;
9. clean reference and measurement frame remain distinct after persistence;
10. required FRONT acceptance completes session while optional 3Q remains unaccepted.

Verification environment:

- Pydantic `2.13.4`;
- pytest `9.0.2`.

Это локальный runtime verification, не GitHub Actions CI.

---

## Contracts status

Canonical shared contracts Integrator пока отсутствуют:

- `ProjectContract`;
- `CapturePackage`;
- `MeasurementCaptureFrame`;
- `ArtifactReference`.

Canonical fixtures под root `/tests/fixtures/contracts/` также отсутствуют.

Internal `ArtifactRecord` и `FrameRecord` намеренно не выдаются за shared contracts и находятся только в ownership Chat 1.

---

## Architecture decisions local to Chat 1

### Validation

Pydantic v2 используется как generic validation/serialization building block. MREA-specific semantics реализуются в собственных моделях/services.

### Offline persistence

Project и CaptureSession сохраняются через replaceable repository protocols. Текущий JSON adapter использует atomic `os.replace` и является локальной offline реализацией, а не глобальным database decision.

### Artifact storage

Image bytes сохраняются content-addressed по SHA-256 через `ArtifactStore` abstraction. Это обеспечивает integrity baseline и не создаёт cloud dependency.

### Capture ordering

`CLEAN_REFERENCE` обязателен до `MEASUREMENT` для каждого view. Measurement semantics/value не входят в ownership Chat 1.

---

## Not implemented yet

### R1 Phase 3 — Calibration Baseline

- Measurement Mat model/version metadata;
- ChArUco/Aruco detector adapter;
- marker visibility result;
- calibration result;
- perspective normalization;
- image registration baseline;
- normalized/rectified artifact relation;
- calibration fixtures.

### R1 Phase 4 — Guided Quality

- blur/focus;
- exposure;
- glare/shadow;
- camera tilt;
- framing;
- perspective warning;
- background quality;
- feature occlusion;
- completeness of views;
- actionable guidance.

### Contract/integration

- canonical CapturePackage builder;
- ProjectContract adapter;
- MeasurementCaptureFrame adapter;
- ArtifactReference adapter;
- canonical fixture validation;
- API;
- mobile UI;
- native camera adapter;
- voice-trigger capture.

---

## Known limitations

- camera image bytes сейчас приходят в service уже готовыми; native camera ownership boundary ещё не реализован;
- artifact store не декодирует изображение и не проверяет фактическое соответствие MIME/extension;
- concurrent writers одного JSON record не поддержаны;
- clean reference replacement/recapture пока не реализован;
- mobile filesystem permissions/atomicity не проверены;
- нет CI;
- нет CV/calibration;
- нет shared-contract compatibility verification.

---

## Current blocker

Внутренние R1 Phase 3/4 могут продолжаться независимо.

Cross-slice integration блокируется отсутствием canonical shared schemas/fixtures Integrator. `CapturePackage v1` нельзя объявлять готовым до их появления.

---

## Immediate next step

### R1 Phase 3 — Calibration Baseline

1. BUILD/REUSE check OpenCV/ArUco/ChArUco;
2. internal Measurement Mat identity/version model;
3. `CalibrationDetector` interface;
4. OpenCV adapter boundary;
5. marker visibility/detection result;
6. homography/calibration result representation;
7. `PerspectiveNormalizer` interface;
8. preserve original frame + create derived rectified artifact;
9. explicit provenance relation original → rectified;
10. tests on generated/synthetic marker fixtures before real camera dataset.

---

## Integration readiness

Ready inside Chat 1:

- Project create/recovery;
- CapturePlan;
- CaptureSession persistence;
- local camera metadata/frame record;
- clean reference/manual measurement frame semantics;
- local evidence artifacts with checksum;
- required-view completion;
- 10 passing tests;
- Phase 1/2 implementation reports and Build/Reuse checks.

Not ready cross-slice:

- canonical contracts;
- CapturePackage;
- calibration/rectification;
- image quality guidance;
- mobile/native camera integration.
