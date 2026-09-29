# Chat 2 — Physical Measurement

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 2  
**Vertical slice:** Physical Measurement  
**Источник истины:** `MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md`  
**Статус документа:** актуализирован при подключении Chat 2 к репозиторию  
**Дата:** 2026-09-29

---

## 1. Назначение роли

Chat 2 реализует полный вертикальный слайс физического измерения: от начала `MeasurementSession` и привязки измерения к конкретным feature/anchors до формирования проверяемого `MeasurementPackage` с provenance и evidence.

Основная задача Chat 2 — превратить физический замер пользователя в структурированную, трассируемую и пригодную для downstream-геометрии метрическую истину.

Ключевой принцип:

```text
physical/user confirmed measurement > vision estimate
```

CV/OCR/voice могут предлагать candidate-значения, но не имеют права молча превращать их в verified metric truth.

---

## 2. Ownership

Chat 2 отвечает за:

- `MeasurementSession`;
- measurement types;
- annotation UX;
- feature anchor selection;
- snapping;
- OCR pipeline;
- voice value;
- user confirmation;
- caliper detection research;
- jaw/contact estimation;
- evidence;
- provenance;
- формирование `MeasurementPackage`.

### Основные компоненты из SSOT

- `MeasurementSessionService`
- `MeasurementTypeRegistry`
- `FeatureAnchorSelector`
- `CaliperDetector`
- `CaliperJawEstimator`
- `DisplayRoiDetector`
- `OcrMeasurementReader`
- `VoiceMeasurementParser`
- `MeasurementConfirmation`
- `MeasurementEvidenceService`
- `MeasurementPackageBuilder`

---

## 3. Что не входит в ownership Chat 2

Chat 2 не отвечает за:

- camera core;
- guided capture;
- final sketch;
- geometry graph;
- CAD;
- lifecycle.

Chat 2 не изменяет самостоятельно:

- shared contracts;
- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- глобальную архитектуру;
- repository-wide ownership;
- cross-slice contracts.

Эти области принадлежат Integrator.

---

## 4. Входы

### Upstream product input

Основной upstream input — `CapturePackage` от Chat 1.

Для Physical Measurement ожидаются категории данных:

- project/part identity;
- доступные capture views;
- clean reference frame;
- measurement frames;
- calibration metadata/reference;
- camera metadata;
- timestamps;
- artifact references;
- contract version.

Точная canonical schema определяется Integrator, а не Chat 2.

### Пользовательские входы

- выбранный measurement type;
- выбранный view;
- anchor A / anchor B либо иной набор anchors по типу измерения;
- ручное numeric value;
- instrument context;
- explicit confirmation;
- позднее — voice value;
- позднее — OCR candidate;
- позднее — CV feature/contact candidates.

---

## 5. Выход

Основной downstream output:

`MeasurementPackage v1`

Он должен содержать проверяемый набор `PhysicalMeasurement`, который может использовать Chat 3 без знания внутренней реализации Chat 2.

Каждый verified `PhysicalMeasurement` должен сохранять как минимум:

- measurement identity;
- measurement type;
- numeric value;
- unit;
- provenance/source;
- confirmation state;
- view reference;
- anchors/feature relation;
- evidence reference либо explicit confirmation согласно contract policy;
- instrument metadata при наличии;
- confidence только как диагностическое поле, а не замену verification;
- uncertainty при наличии/поддержке contract;
- contract/version linkage через package.

---

## 6. Типы измерений

Минимальный набор из SSOT:

- `LINEAR_EXTERNAL`
- `LINEAR_INTERNAL`
- `THICKNESS`
- `DEPTH`
- `DIAMETER_EXTERNAL`
- `DIAMETER_INTERNAL`
- `RADIUS`
- `ANGLE`
- `CENTER_DISTANCE`
- `SLOT_WIDTH`
- `SURFACE_DISTANCE`

`MeasurementTypeRegistry` должен централизовать доступные типы и их локальные правила ввода/anchor semantics, не превращаясь в shared contract без решения Integrator.

---

## 7. Phase A — Manual Measurement Baseline

Первая обязательная фаза:

```text
Manual anchors + manual value
```

Базовый поток:

```text
CapturePackage
→ MeasurementSession
→ select view
→ select measurement type
→ select anchor(s)
→ enter numeric value
→ attach evidence / explicit confirmation
→ confirm
→ PhysicalMeasurement
→ MeasurementPackage
```

### Цель Phase A

Получить полезный продуктовый baseline без зависимости от рискованных CV/OCR-задач.

Пользователь уже должен иметь возможность:

1. выбрать нужный view;
2. указать, что именно измеряется;
3. привязать размер к anchors/features;
4. вручную ввести значение;
5. подтвердить его;
6. открыть evidence;
7. увидеть provenance;
8. сохранить измерение в `MeasurementPackage`.

---

## 8. Phase B — Snapping

После стабильного manual baseline добавляется snapping к detected features.

Правило:

```text
snap = interaction assistance
snap != metric truth
```

Snapping помогает выбрать anchor, но не должен автоматически подменять физический measurement.

Если snap uncertain или ambiguous, пользователь должен иметь возможность:

- выбрать другой candidate;
- отключить snapping;
- оставить manual anchor;
- увидеть, что anchor выбран автоматически/полуавтоматически.

---

## 9. Phase C — OCR

OCR используется как proposal source, а не как автоматическая истина.

Поток:

```text
Measurement Frame
→ Display ROI candidate
→ OCR candidate
→ normalization
→ confidence/validation
→ user confirmation
→ PhysicalMeasurement
```

Критическое правило:

```text
OCR candidate cannot silently become verified
```

Для LCD caliper требуется отдельная validation на собственном dataset, поскольку generic OCR сам по себе не гарантирует надёжность в реальных углах, бликах и освещении.

---

## 10. Phase D — Voice value

Voice parser может:

- принять продиктованное значение;
- предложить нормализованный numeric candidate;
- запросить подтверждение;
- обработать correction flow.

Пример логики:

```text
"замер сорок два восемнадцать"
→ 42.18 mm candidate
→ confirmation
→ VOICE_REPORTED + USER_CONFIRMED
```

Voice не отменяет requirement provenance/confirmation.

---

## 11. Phase E — Caliper / Jaw / Contact CV

Это исследовательская high-risk фаза и она не блокирует MVP.

Исследовательский pipeline:

```text
Measurement Frame
→ Registration
→ Caliper detection
→ Jaw detection
→ Contact-region estimation
→ Feature association
→ Display ROI
→ OCR/value extraction
→ candidate measurement
→ user confirmation
→ PhysicalMeasurement
```

Chat 2 должен отдельно исследовать:

- caliper localization;
- jaw geometry;
- contact point/region estimation;
- связь jaw contacts с feature;
- display ROI detection;
- confidence calibration.

Даже при высоком confidence результат остаётся candidate до разрешённого contract-ом физического/пользовательского подтверждения.

---

## 12. Provenance policy

Базовые provenance категории SSOT:

- `MANUAL_MEASURED`
- `DEVICE_REPORTED`
- `OCR_MEASURED`
- `VOICE_REPORTED`
- `VISION_DETECTED`
- `CALIBRATION_DERIVED`
- `GEOMETRY_DERIVED`
- `AI_INFERRED`
- `USER_CONFIRMED`

Для Chat 2 наиболее важны:

- `MANUAL_MEASURED`;
- `DEVICE_REPORTED`;
- `OCR_MEASURED`;
- `VOICE_REPORTED`;
- `VISION_DETECTED` как candidate source;
- `USER_CONFIRMED` как confirmation event/state.

Точная модель хранения provenance должна быть утверждена shared contract-ом Integrator.

---

## 13. Source priority

Базовый приоритет SSOT:

```text
DEVICE_REPORTED / MANUAL_MEASURED
>
OCR_MEASURED / VOICE_REPORTED after confirmation
>
CALIBRATION_DERIVED
>
VISION_DETECTED
>
GEOMETRY_DERIVED
>
AI_INFERRED
```

Chat 2 обязан сохранять конфликт, а не молча исправлять measurement.

Пример:

```text
Verified physical measurement: 42.18 mm
Vision estimate: 41.72 mm
Status: CONFLICT
```

---

## 14. Evidence Chain

Каждый verified dimension должен иметь обратную трассировку.

Для зоны Chat 2 важный фрагмент цепочки:

```text
PhysicalMeasurement M001
↓
Evidence Frame FRAME_001
↓
Исходный measurement frame
```

Downstream система должна иметь возможность продолжить цепочку:

```text
CAD Dimension
→ Sketch Dimension
→ PhysicalMeasurement
→ Evidence Frame
→ original source
```

Evidence нельзя удалять скрыто или заменять derived representation без сохранения origin.

---

## 15. MeasurementSession

`MeasurementSession` должен быть отдельной управляемой сессией, а не набором несвязанных numeric inputs.

Минимальная логическая state model для внутренней реализации должна учитывать:

- session start;
- current project/part;
- active view;
- pending measurement;
- selected measurement type;
- selected anchors;
- candidate value;
- evidence reference;
- confirmation state;
- accepted measurement;
- rejected/corrected candidate;
- session persistence;
- package build/close.

Финальные имена полей state model локальны Chat 2 до тех пор, пока не пересекают shared contract.

---

## 16. Offline-first требования

Measurement workflow должен работать без cloud-only зависимости.

Обязательные свойства:

- session сохраняется локально;
- ручной ввод работает без сети;
- evidence reference не теряется;
- frames не теряются;
- pending measurements не исчезают при interruption;
- синхронизация может происходить позже;
- OCR/voice provider не должен делать базовый manual workflow зависимым от облака.

---

## 17. Build / Reuse baseline

Перед нетривиальной функцией требуется Build / Reuse Check.

Предварительный baseline:

### OCR

Используем готовый OCR engine/provider.

Пишем сами:

- ROI orchestration;
- normalization;
- LCD-specific validation;
- candidate/confirmation policy;
- measurement integration.

### Voice

Используем platform speech recognition как baseline.

Пишем сами:

- measurement phrase parsing;
- numeric normalization;
- correction flow;
- confirmation policy;
- domain integration.

### CV

Используем OpenCV/готовые модели как building blocks.

Пишем сами:

- measurement-specific orchestration;
- caliper/jaw/contact association logic;
- evidence/provenance linkage;
- confidence policy;
- user confirmation workflow.

Generic OCR, generic speech-to-text и generic segmentation models с нуля не реализуются без отдельной причины.

---

## 18. Acceptance Criteria Chat 2

Слайс должен подтвердить:

- каждый `PhysicalMeasurement` имеет provenance;
- verified measurement имеет evidence или explicit confirmation согласно canonical contract;
- OCR не может автоматически стать verified;
- evidence frame можно открыть;
- measurement связан с view и anchors;
- `MeasurementPackage` проходит schema validation.

Дополнительно для Phase A необходимо проверить:

- manual numeric input;
- создание и завершение measurement session;
- correction/rejection path;
- package determinism для одного и того же подтверждённого набора measurements;
- сохранение evidence references;
- отсутствие скрытой коррекции значений.

---

## 19. Тестовая стратегия Chat 2

### Unit

Проверяются локальные domain-компоненты:

- measurement type rules;
- numeric normalization;
- confirmation state transitions;
- anchor selection rules;
- provenance assignment;
- package building logic.

### Contract

После появления canonical schemas:

- `CapturePackage` читается;
- `MeasurementPackage` валидируется;
- backward compatibility проверяется по версии contract;
- invalid input не скрывается.

### Integration

Phase A:

```text
Capture fixture
→ manual measurement
→ confirmation
→ MeasurementPackage
```

### OCR dataset later

Нужен собственный LCD dataset:

- разные значения;
- разные углы;
- разное освещение;
- glare;
- разные модели штангенциркуля later.

### Physical verification

Critical geometry должна проверяться реальным физическим инструментом, а не только фото-derived оценкой.

---

## 20. Технические риски Chat 2

### High

- reliable caliper detection;
- jaw/contact estimation;
- LCD OCR в реальных условиях;
- feature association при occlusion и руках пользователя.

### Medium

- voice recognition/false positives;
- snapping ambiguity;
- registration robustness между clean frame и measurement frame.

### Low

- manual measurement annotation;
- evidence persistence;
- basic measurement session state;
- REST/API слой после утверждения архитектуры.

Roadmap Chat 2 не должен начинаться с High-risk задач.

---

## 21. Ограничения на разработку

1. Не выдумывать shared schemas.
2. Не менять shared contracts без Change Request.
3. Не делать OCR/CV результат verified без подтверждения.
4. Не скрывать conflicts между physical measurement и vision-derived estimate.
5. Не менять measurement в пользу geometry/AI.
6. Не удалять evidence.
7. Не делать cloud-only measurement architecture.
8. Не затрагивать camera core Chat 1.
9. Не реализовывать final sketch Chat 3.
10. Не смешивать experimental caliper CV с обязательным MVP path.

---

## 22. Зависимости от соседних слайсов

### Chat 1 → Chat 2

Chat 2 потребляет `CapturePackage` и evidence/measurement-frame references.

Chat 2 не должен зависеть от внутреннего camera implementation Chat 1.

### Chat 2 → Chat 3

Chat 2 выдаёт `MeasurementPackage`.

Chat 3 должен иметь возможность использовать verified physical measurements независимо от OCR/CV implementation Chat 2.

### Integrator

Integrator утверждает shared schemas, fixtures, versioning и contract migrations.

---

## 23. Change Request к Integrator

```text
CHANGE_REQUEST

Requester:
Chat 2 — Physical Measurement

Contract:
CapturePackage
MeasurementCaptureFrame
PhysicalMeasurement
MeasurementPackage
ArtifactReference

Problem:
SSOT определяет semantics, ownership и acceptance criteria,
но в текущем repository canonical v1 schemas/fixtures не обнаружены.

Current behavior:
Chat 2 может документировать и реализовывать внутренний manual workflow,
но не может честно выполнить downstream/upstream contract validation.

Requested change:
Утвердить и добавить canonical v1 schemas + fixtures для:
- CapturePackage
- MeasurementCaptureFrame
- PhysicalMeasurement
- MeasurementPackage
- ArtifactReference

Дополнительно утвердить:
- measurement type representation;
- unit representation;
- provenance/source representation;
- confirmation model;
- anchor representation;
- view reference;
- evidence reference;
- instrument metadata representation;
- confidence/uncertainty semantics;
- package version field;
- invalid/conflict representation where cross-slice relevant.

Reason:
Без canonical contract Chat 2 не может гарантировать совместимость
с Chat 1 upstream и Chat 3 downstream.

Affected chats:
Integrator
Chat 1
Chat 2
Chat 3

Backward compatible:
YES — canonical v1 contracts ещё не обнаружены в repository.

Migration:
Not applicable for initial v1 publication.
```

---

## 24. Текущее состояние репозитория при подключении Chat 2

На момент подключения:

- repository существует;
- default branch: `main`;
- рабочая область Chat 1 уже существует;
- shared contracts/fixtures v1 в доступном root repository tree пока не обнаружены;
- код Chat 2 ещё не реализован;
- создана отдельная рабочая область `chat_2_physical_measurement/`;
- документация роли создана в `chat_2_physical_measurement/docs/`.

---

## 25. Следующий шаг

После появления Integrator baseline:

1. повторно прочитать актуальный repository tree;
2. найти canonical contracts/fixtures;
3. проверить их версии и ownership;
4. зафиксировать Build / Reuse Check для первого нетривиального dependency;
5. реализовать Phase A domain/state model;
6. реализовать manual anchor selection;
7. реализовать manual numeric input;
8. реализовать explicit confirmation;
9. реализовать evidence/provenance linkage;
10. собрать `MeasurementPackage`;
11. добавить unit/contract/integration tests;
12. обновить этот документ и Implementation Report;
13. только после стабильного Phase A переходить к Phase B snapping.
