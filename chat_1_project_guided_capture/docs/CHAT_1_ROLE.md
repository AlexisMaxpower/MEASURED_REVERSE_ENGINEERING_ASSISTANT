# Chat 1 — Project & Guided Capture

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 1  
**Vertical slice:** Project & Guided Capture  
**Источник истины:** `../MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md`  
**Статус документа:** актуализирован при подключении Chat 1 к репозиторию  
**Дата:** 2026-09-29

---

## 1. Назначение роли

Chat 1 реализует полный вертикальный слайс от создания проекта до формирования валидного `CapturePackage`, который может быть передан downstream-слайсам.

Основная задача: обеспечить воспроизводимый, проверяемый и удобный процесс получения исходных визуальных данных детали до того, как система начнёт интерпретировать физические измерения или строить геометрию.

---

## 2. Ownership

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
- формирование `CapturePackage`.

### Основные компоненты

- `ProjectService`
- `CapturePlanService`
- `CameraSession`
- `ImageQualityAnalyzer`
- `CalibrationDetector`
- `CaptureRegistration`
- `ReferenceFrameBuilder`
- `VoiceCaptureTrigger`
- `CapturePackageBuilder`

---

## 3. Что не входит в ownership Chat 1

Chat 1 не отвечает за:

- смысл measurement;
- final measurement value;
- final OCR semantics;
- `PhysicalMeasurement` как метрологически подтверждённый результат;
- feature anchors как measurement semantics;
- geometry/sketch;
- CAD;
- lifecycle.

Chat 1 не изменяет самостоятельно:

- shared contracts;
- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- глобальную архитектуру;
- cross-slice ownership.

Эти области принадлежат Integrator.

---

## 4. Входы

### Пользовательские/физические входы

- project context;
- описание детали и проблемы;
- камера/фотографии;
- Measurement Mat;
- camera metadata;
- команды захвата;
- voice trigger на Hands-Free этапе.

### Shared contracts, которые потребляет или производит Chat 1

- `ProjectContract`;
- `CapturePackage`;
- `MeasurementCaptureFrame`;
- `ArtifactReference`.

Их canonical schemas должны утверждаться Integrator и версионироваться.

---

## 5. Выход

Основной downstream output:

`CapturePackage v1`

Он должен содержать достаточно данных, чтобы Chat 2 мог начать Physical Measurement без зависимости от внутренней реализации Chat 1.

Минимально ожидаемые категории данных:

- project identity/reference;
- captured views;
- clean reference frame;
- measurement frames;
- calibration reference/metadata;
- camera metadata;
- timestamps;
- image-quality results/warnings;
- artifact references;
- contract version.

Точная schema не фиксируется этим документом, потому что shared contracts принадлежат Integrator.

---

## 6. Capture workflow

Базовый поток Chat 1:

```text
Project
→ CapturePlan
→ CaptureSession
→ Guided Capture
→ Image Quality Analysis
→ Measurement Mat Detection
→ Calibration
→ Perspective Normalization
→ CleanReferenceFrame
→ MeasurementCaptureFrame
→ CapturePackage
```

Ключевой принцип: clean reference frame должен храниться отдельно от measurement frames. Measurement frames остаются исходными evidence-артефактами и не должны механически накладываться друг на друга для построения финального clean view.

---

## 7. Guided Capture checks

Планируемые проверки:

- marker visibility;
- focus;
- blur;
- exposure;
- shadow;
- glare;
- camera tilt;
- object framing;
- perspective distortion;
- background quality;
- feature occlusion;
- completeness of views.

Результат проверки должен быть объясним пользователю как actionable warning, а не только численный score.

---

## 8. CapturePlan

Поддерживаемые SSOT виды:

- `FRONT`
- `LEFT`
- `RIGHT`
- `TOP`
- `BOTTOM`
- `REAR`
- `DETAIL_A`
- `DETAIL_B`
- `OPTIONAL_3Q`

Система может рекомендовать дополнительные виды, но не должна утверждать, что скрытая геометрия полностью восстановлена при недостатке данных.

---

## 9. Measurement Mat

Measurement Mat используется для:

- определения рабочей плоскости;
- калибровки;
- perspective correction;
- масштаба изображения;
- регистрации кадров;
- обнаружения смещения камеры;
- единой XY-системы.

Measurement Mat не заменяет физический измерительный инструмент для verified metric dimensions.

---

## 10. MVP Chat 1

Согласно разделу Chat 1 SSOT:

1. project;
2. CapturePlan;
3. camera;
4. clean reference frame;
5. marker detection;
6. perspective normalization;
7. manual measurement frame;
8. voice-trigger measurement frame;
9. quality warnings;
10. CapturePackage v1.

### Roadmap reconciliation

Глобальный Roadmap SSOT относит `voice trigger` к R4 — Hands-Free, тогда как локальный MVP/Acceptance Chat 1 включает voice-trigger measurement frame.

До решения Integrator применяется следующая рабочая трактовка:

- R1: manual capture baseline без обязательной voice automation;
- R4: voice-trigger extension;
- итоговый Chat 1 slice должен выполнить acceptance по voice-trigger capture event.

Это трактовка состояния разработки, а не изменение SSOT.

---

## 11. Acceptance Criteria

Slice Chat 1 должен подтвердить:

- project создаётся и восстанавливается;
- `FRONT` view может быть завершён;
- clean frame отделён от measurement frames;
- calibration сохраняется;
- каждый frame имеет timestamp и camera metadata;
- voice trigger создаёт capture event;
- `CapturePackage` проходит schema validation.

---

## 12. Offline-first требования

Capture workflow должен работать без cloud-only зависимости:

- session хранится локально;
- frames не теряются при отсутствии сети;
- basic calibration доступна локально;
- синхронизация может выполняться позже.

---

## 13. Build / Reuse baseline

Перед реализацией каждого нетривиального CV/camera компонента заполняется Build / Reuse Check.

Предварительный baseline из SSOT:

- OpenCV используется как строительный блок для CV;
- marker detection/calibration не пишутся с нуля без необходимости;
- generic segmentation model не разрабатывается с нуля;
- platform speech recognition используется для первоначального voice-trigger spike;
- собственными остаются orchestration, workflow, quality policy, capture state machine и формирование downstream package.

---

## 14. Технические риски Chat 1

### Medium

- marker calibration robustness;
- perspective correction;
- segmentation/background preparation;
- voice trigger reliability.

### Low

- project model;
- REST/API слой после утверждения архитектуры;
- сохранение базового capture state.

High-risk caliper/jaw/OCR research не должен блокировать R1 и относится преимущественно к Chat 2 / более поздним этапам.

---

## 15. Ограничения на разработку

1. Не выдумывать shared schemas.
2. Не менять verified physical measurement — Chat 1 вообще не является владельцем final measurement semantics.
3. Не выдавать image-derived масштаб/геометрию за physical measurement.
4. Не использовать cloud-only camera/capture architecture.
5. Не затрагивать директории других vertical slices.
6. Не делать CV/AI результат скрытой истиной: результат должен оставаться candidate/diagnostic до соответствующего подтверждения downstream.

---

## 16. Change Request к Integrator

```text
CHANGE_REQUEST

Requester:
Chat 1 — Project & Guided Capture

Contract:
ProjectContract
CapturePackage
MeasurementCaptureFrame
ArtifactReference

Problem:
SSOT определяет назначение и ownership contracts,
но не задаёт полные versioned schemas.

Current behavior:
Есть концептуальные имена и требования, но нет canonical v1 schemas/fixtures.

Requested change:
Утвердить v1 schemas и canonical fixtures для:
- ProjectContract
- CapturePackage
- MeasurementCaptureFrame
- ArtifactReference

Также зафиксировать:
- CaptureViewType enum;
- camera metadata schema;
- calibration metadata schema;
- quality-warning representation;
- clean_reference_frame reference;
- measurement frame list;
- timestamps;
- artifact identifiers;
- contract version field.

Reason:
Без этого Chat 1 может реализовать внутренний domain,
но не может честно выполнить contract validation
и гарантировать совместимость с Chat 2.

Affected chats:
Integrator
Chat 1
Chat 2
potentially Chat 3

Backward compatible:
YES — contracts ещё не реализованы.

Migration:
Not applicable.
```

---

## 17. Текущий следующий шаг

До утверждения shared contracts можно безопасно проектировать и реализовывать внутренние компоненты Chat 1 только там, где их интерфейс не фиксирует глобальную schema.

При появлении Integrator baseline порядок работы:

1. сверить repository structure;
2. прочитать canonical contracts/fixtures;
3. провести Build / Reuse Check по camera/CV зависимостям;
4. реализовать Project/CapturePlan domain;
5. реализовать manual capture path;
6. добавить calibration и perspective normalization;
7. добавить quality analysis;
8. сформировать `CapturePackage` через утверждённую schema;
9. добавить contract/integration tests;
10. обновить эту документацию и Implementation Report.
