# Chat 1 — Project & Guided Capture

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 1  
**Vertical slice:** Project & Guided Capture  
**Источник истины продукта:** `../MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md`  
**Canonical integration authority:** Chat 6 — Orchestrator / Repository Integrator  
**Current directive:** `OD-2026-09-29-001`  
**Contract baseline:** `mrea.contracts.v1`  
**Дата актуализации:** 2026-09-29

## 1. Назначение роли

Chat 1 реализует вертикальный слайс от создания Project и контекста детали до формирования canonical `CapturePackage`, который downstream-слайсы могут потреблять без знания внутренней реализации Capture.

Основная задача — получить воспроизводимые, проверяемые visual evidence artifacts и calibration context до того, как система начинает интерпретировать физические измерения или строить геометрию.

## 2. Source-of-truth hierarchy

Для Chat 1 действует порядок:

1. current repository state on `main`;
2. canonical shared contracts in `core/contracts/`;
3. canonical fixtures in `tests/fixtures/contracts/`;
4. product SSOT + Chat 6 orchestration state/directives;
5. Chat 1 local documentation.

Если slice-local документ противоречит canonical contract, побеждает `core/contracts/`.

## 3. Ownership Chat 1

Chat 1 отвечает за:

- Project creation;
- Part initial context;
- CapturePlan;
- Camera workflow;
- Guided Capture;
- Measurement Mat detection;
- calibration;
- clean reference frame;
- measurement frame capture;
- voice capture trigger;
- image quality analysis;
- background/object preparation;
- формирование canonical `CapturePackage` через adapter boundary.

Основные компоненты/зоны ответственности:

- `ProjectService`;
- `CapturePlanService`;
- CaptureSession state/workflow;
- `ArtifactStore` abstraction;
- `CalibrationDetector`;
- `CalibrationService`;
- future `CaptureRegistration` / perspective normalization;
- future `ImageQualityAnalyzer`;
- future `VoiceCaptureTrigger`;
- `CanonicalContractBuilder` как outward adapter к Integrator-owned contracts.

## 4. Что не входит в ownership

Chat 1 не владеет:

- measurement meaning;
- final measurement value;
- final OCR semantics;
- `PhysicalMeasurement` semantics;
- feature anchors как measurement semantics;
- geometry/sketch;
- CAD;
- lifecycle.

Chat 1 не изменяет самостоятельно:

- `core/contracts/`;
- `core/domain/shared/`;
- `tests/fixtures/contracts/`;
- глобальную архитектуру;
- cross-slice ownership.

Любое backward-incompatible изменение shared contract требует Change Request к Chat 6.

## 5. Canonical inputs and outputs

Текущие canonical источники:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/project_v1.json`;
- `tests/fixtures/contracts/capture_package_v1.json`.

Chat 1 производит наружу:

- `ProjectContract v1`;
- `CapturePackage v1`;
- вложенные canonical `ArtifactReference`;
- вложенные canonical `MeasurementCaptureFrame`;
- optional per-view calibration object.

Internal models (`Project`, `ArtifactRecord`, `FrameRecord`, `CaptureSession`, `CalibrationResult`) остаются slice-local и не выдаются за shared contracts.

## 6. Canonical boundary policy

Утверждённые правила:

- wire IDs — opaque non-empty strings;
- UUID внутри Chat 1 допустим и сериализуется наружу как opaque string;
- Project имеет стабильные `project_id` и `part_id`;
- legacy Project без `part_id` получает deterministic stable backfill;
- timestamps выходят в UTC/RFC3339;
- `CapturePackage` содержит captured views;
- каждый emitted view содержит ровно один clean reference artifact;
- measurement frames остаются отдельными evidence artifacts;
- calibration относится к clean reference того же view;
- Chat 1 не меняет physical measurement semantics.

## 7. Capture workflow

Целевой поток:

```text
Project
→ CapturePlan
→ CaptureSession
→ Camera / Guided Capture
→ Clean Reference
→ Measurement Mat Detection
→ Calibration
→ Perspective Normalization
→ Measurement Frames
→ Quality Analysis
→ Canonical CapturePackage
```

Clean reference и measurement frames должны оставаться отдельными immutable evidence artifacts.

## 8. CapturePlan

Поддерживаемые canonical/SSOT виды:

- `FRONT`;
- `LEFT`;
- `RIGHT`;
- `TOP`;
- `BOTTOM`;
- `REAR`;
- `DETAIL_A`;
- `DETAIL_B`;
- `OPTIONAL_3Q`.

Текущий safe implicit baseline — `FRONT`. `OPTIONAL_3Q` не блокирует completion required views.

## 9. Measurement Mat и calibration

Measurement Mat используется для:

- fiducial detection;
- определения рабочей плоскости;
- calibration;
- perspective correction;
- регистрации в единой XY-системе;
- перехода `IMAGE_PX -> MAT_XY_MM`.

Текущая реализация использует OpenCV ChArUco и RANSAC homography. Measurement Mat не заменяет verified physical measurement instrument.

Объективная calibration evidence включает:

- detected marker count;
- detected ChArUco corner count;
- corner IDs;
- 3x3 homography;
- reprojection RMSE in mm;
- clean-reference provenance.

Canonical `calibration.quality` пока остаётся `null`, потому что утверждённой scalar quality formula нет.

## 10. Guided Capture checks — planned

Будущие проверки:

- marker visibility;
- focus/blur;
- exposure;
- shadow/glare;
- camera tilt;
- object framing;
- perspective distortion;
- background quality;
- feature occlusion;
- completeness of views.

Результат должен быть actionable warning, а не скрытый AI/CV verdict.

## 11. Offline-first

Capture workflow должен работать без cloud-only зависимости:

- Project и CaptureSession сохраняются локально;
- image artifacts хранятся локально через replaceable `ArtifactStore`;
- basic calibration выполняется локально;
- данные не теряются при отсутствии сети;
- будущая синхронизация не должна менять domain semantics.

Текущие adapters: atomic JSON repositories + content-addressed filesystem artifact store with SHA-256 verification.

## 12. Build / Reuse policy

Не переизобретаем generic infrastructure:

- Pydantic — validation/serialization;
- OpenCV — ArUco/ChArUco detection, image decode, homography primitives;
- NumPy — numerical arrays;
- jsonschema — canonical contract tests.

MREA-own code: orchestration, capture state machine, provenance policy, mat identity/configuration, boundary mapping, acceptance rules и product-specific quality policy.

## 13. Реализовано к концу Прохода 1

### Phase 1

- Project/Part context;
- create/recovery/archive;
- stable `project_id` / `part_id`;
- deterministic CapturePlan;
- offline repository abstraction.

### Phase 2

- CaptureSession persistence;
- CameraMetadata;
- clean/measurement separation;
- content-addressed artifacts + SHA-256;
- required-view completion semantics.

### Canonical integration gate

- canonical `ProjectContract v1` adapter;
- canonical `CapturePackage v1` builder;
- ArtifactReference/MeasurementCaptureFrame mapping;
- deterministic opaque package/view IDs;
- JSON Schema validation;
- FRONT acceptance target `OD-2026-09-29-001` satisfied.

### Phase 3 calibration baseline

- `MeasurementMatProfile`;
- `CalibrationResult` persistence;
- `CalibrationDetector` abstraction;
- `OpenCvCharucoCalibrationDetector`;
- ChArUco detection;
- RANSAC homography to `MAT_XY_MM`;
- canonical non-null calibration mapping;
- synthetic integration test.

## 14. Verification status

Latest full local regression:

```text
13 passed in 1.07s
```

Synthetic calibration fixture:

- 5x7 ChArUco board;
- 24 ChArUco corners;
- marker detection succeeds;
- 9-value homography;
- reprojection RMSE `< 0.001 mm`;
- resulting canonical CapturePackage validates against Integrator-owned schema.

Не проверено:

- GitHub Actions CI;
- printed physical mat;
- phone lens distortion / intrinsics;
- physical mm accuracy;
- real-world blur/glare/oblique capture robustness;
- mobile/native camera runtime.

## 15. Acceptance criteria tracking

- project создаётся и восстанавливается — DONE;
- FRONT view может быть завершён — DONE;
- clean frame отделён от measurement frames — DONE;
- calibration сохраняется — DONE;
- frame имеет timestamp/camera metadata — DONE;
- CapturePackage schema validation — DONE;
- marker detection — DONE baseline;
- perspective normalization — NOT YET;
- quality warnings — NOT YET;
- voice trigger creates capture event — NOT YET, planned Hands-Free/R4 extension.

## 16. Closed Change Request

Первоначальный запрос на canonical `ProjectContract`, `CapturePackage`, `MeasurementCaptureFrame`, `ArtifactReference` **закрыт**: Chat 6 опубликовал `mrea.contracts.v1` и canonical fixtures.

Новый Change Request сейчас не требуется. Любые будущие несовместимые contract changes должны идти через Chat 6.

## 17. Immediate next technical target

После интеграционной проверки Chat 6 следующий технический target Chat 1:

1. perspective-normalized derived image artifact;
2. deterministic `MAT_XY_MM` raster definition;
3. source clean-reference → rectified artifact provenance;
4. synthetic perspective-distortion warp test;
5. затем Guided Quality baseline.

До новой директивы Chat 6 shared contracts не меняются.
