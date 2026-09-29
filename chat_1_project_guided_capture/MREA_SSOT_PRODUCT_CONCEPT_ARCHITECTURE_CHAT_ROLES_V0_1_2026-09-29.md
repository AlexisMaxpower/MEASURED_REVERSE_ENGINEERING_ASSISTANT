# MREA — Measured Reverse Engineering Assistant
## Product Concept, Technology Architecture, Development Matrix & Multi-Chat Ownership
### Single Source of Truth — v0.1

**Дата:** 2026-09-29  
**Статус:** архитектурный baseline для начала разработки  
**Язык документации:** русский  
**Язык идентификаторов кода:** английский  
**Назначение:** единый источник истины для параллельной разработки продукта несколькими чатами/агентами.

---

# 0. Как использовать этот документ

Этот файл является **Single Source of Truth (SSOT)** для проекта MREA.

Любой новый чат получает этот файл и короткую команду:

> Ты Chat N. Твоя роль, ownership, входные и выходные контракты, критерии приёмки и ограничения определены в этом SSOT. Работай строго в рамках своего вертикального слайса. Shared contracts не меняй самостоятельно. Если контракт недостаточен — подготовь Change Request для Integrator.

Пример:

> Ты Chat 3. Работай по роли Chat 3 из SSOT. Начни с восстановления контекста, перечисли свои входные/выходные контракты и реализуй свой вертикальный слайс, используя fixture-данные. Не меняй чужие модули.

---

# 1. Главная организационная модель

Продукт разрабатывается как **матрица строк и столбцов**.

## 1.1. Строки

Строки — горизонтальные слои системы:

- UX / mobile interaction;
- domain model;
- CV / vision;
- application logic;
- backend/API;
- storage;
- export/integration;
- validation;
- tests;
- documentation.

## 1.2. Столбцы

Столбцы — независимые вертикальные продуктовые слайсы.

Каждый чат владеет одним столбцом целиком и реализует его **от пользовательского сценария до данных, тестов и документации**.

Основные слайсы:

1. **Chat 1 — Project & Guided Capture**
2. **Chat 2 — Physical Measurement**
3. **Chat 3 — Geometry & Semi-Automatic Sketch**
4. **Chat 4 — CAD Bridge & Verification**
5. **Chat 5 — Lifecycle & Engineering Knowledge**

Отдельная роль:

6. **Integrator / Main Chat** — архитектура, shared contracts, интеграция, release gate.

## 1.3. Почему не делим по технологиям

Нельзя делить так:

- один чат пишет frontend;
- второй backend;
- третий CV;
- четвёртый БД.

Это создаст постоянные блокировки и размытый ownership.

Нужно делить так:

- Chat 1 полностью делает Capture;
- Chat 2 полностью делает Measurements;
- Chat 3 полностью делает Geometry;
- Chat 4 полностью делает CAD;
- Chat 5 полностью делает Lifecycle.

Каждый чат получает upstream fixture и обязан выдавать downstream contract.

---

# 2. Название и суть продукта

## 2.1. Рабочее название

**MREA — Measured Reverse Engineering Assistant**

## 2.2. Одно предложение

MREA — мобильная и настольная система для **доверяемого reverse engineering физических деталей**: от правильной съёмки и ручных измерений до полуавтоматического CAD-эскиза, проверки размеров, изготовления, испытаний, ревизий и истории эксплуатации.

## 2.3. Основная ценность

Продукт закрывает разрыв между:

```text
ФИЗИЧЕСКАЯ ДЕТАЛЬ
        ↓
ФОТО / ИЗМЕРЕНИЯ
        ↓
СТРУКТУРИРОВАННАЯ ГЕОМЕТРИЯ
        ↓
ПОЛУАВТОМАТИЧЕСКИЙ ЭСКИЗ
        ↓
CAD
        ↓
ИЗГОТОВЛЕНИЕ
        ↓
ЭКСПЛУАТАЦИЯ
        ↓
РЕВИЗИЯ
```

---

# 3. Какая проблема решается

Обычный reverse engineering небольшой физической детали часто выглядит так:

- деталь фотографируется как попало;
- размеры измеряются штангенциркулем;
- часть значений записывается в заметки;
- часть — на бумагу;
- часть — поверх фото;
- фотографии и размеры не связаны;
- в CAD данные перебиваются повторно вручную;
- сложно понять, откуда появился конкретный размер;
- нет формальной связи между CAD-ревизией и реально изготовленной деталью;
- нет истории поломок и успешных решений;
- инженерный опыт остаётся в голове конкретного человека.

MREA превращает этот хаотичный процесс в единый проверяемый workflow.

---

# 4. Принцип продукта

## 4.1. MREA не заменяет инженера

Система не должна утверждать:

> «AI сам понял деталь и гарантированно построил правильную модель».

Она должна:

1. помочь корректно снять объект;
2. помочь корректно измерить;
3. зафиксировать источник каждого измерения;
4. распознать геометрические кандидаты;
5. создать полуавтоматический эскиз;
6. показать, где факт, а где предположение;
7. проверить перенос размеров в CAD;
8. сохранить историю изготовления и эксплуатации.

## 4.2. Главный метрологический закон

**Ни один алгоритм CV/AI не имеет права молча заменить физическое измерение пользователя.**

Каждое значение и каждая геометрическая сущность имеют `provenance` — происхождение.

Базовые категории:

- `MANUAL_MEASURED`
- `DEVICE_REPORTED`
- `OCR_MEASURED`
- `VOICE_REPORTED`
- `VISION_DETECTED`
- `CALIBRATION_DERIVED`
- `GEOMETRY_DERIVED`
- `AI_INFERRED`
- `USER_CONFIRMED`

## 4.3. Приоритет источников

Базовый приоритет:

```text
DEVICE_REPORTED / MANUAL_MEASURED
>
OCR_MEASURED / VOICE_REPORTED после подтверждения
>
CALIBRATION_DERIVED
>
VISION_DETECTED
>
GEOMETRY_DERIVED
>
AI_INFERRED
```

## 4.4. Никакой скрытой коррекции

Если пользователь измерил:

```text
42.18 мм
```

а CV по фотографии считает:

```text
41.72 мм
```

система не исправляет измерение.

Она показывает конфликт:

```text
Verified physical measurement: 42.18 mm
Vision estimate: 41.72 mm
Status: CONFLICT
```

---

# 5. Что мы НЕ изобретаем заново

MREA — собственный продукт, но не повод переписывать фундаментальные технологии без причины.

## 5.1. Не пишем с нуля

- CAD kernel;
- аналог SolidWorks;
- аналог AutoCAD;
- универсальный PDM/PLM;
- OCR engine общего назначения;
- generic speech-to-text;
- generic segmentation foundation model;
- photogrammetry engine;
- SQL database engine;
- object storage;
- универсальный geometry solver, если существующая библиотека подходит;
- DXF/STEP parser, если есть стабильная библиотека.

## 5.2. Пишем сами

- guided reverse-engineering workflow;
- measurement session UX;
- hands-free measurement capture;
- привязку физического измерения к feature;
- provenance;
- evidence chain;
- aggregation measurement frames;
- dimensioned clean view;
- geometry graph;
- SketchPackage;
- CAD verification;
- lifecycle;
- engineering knowledge;
- orchestration готовых CV/OCR/speech/CAD компонентов.

---

# 6. Основной пользовательский сценарий

```text
Создать проект
↓
Описать деталь и неисправность
↓
Приложение подсказывает, как снять деталь
↓
Сделать чистые виды
↓
Запустить Measurement Session
↓
Измерять штангенциркулем
↓
Говорить «замер»
↓
Камера автоматически фиксирует measurement frame
↓
Приложение извлекает/принимает размер
↓
Размер связывается с feature
↓
Формируется чистый dimensioned view
↓
Строится полуавтоматический SketchPackage
↓
Импорт в SolidWorks / AutoCAD
↓
CAD Verification
↓
Финальное моделирование
↓
Изготовление
↓
Установка
↓
Испытание
↓
Failure / success
↓
REV02 / REV03 / ...
↓
Накопление инженерных знаний
```

---

# 7. Project Context

При создании проекта пользователь задаёт:

- название;
- тип детали;
- оборудование;
- узел;
- назначение;
- проблема;
- причина reverse engineering;
- материал оригинала, если известен;
- способ изготовления оригинала, если известен;
- предполагаемый способ изготовления новой детали;
- фото поломки;
- комментарии.

Пример:

```text
Project: FREEZER_DOOR_001
Part: внутренняя дверца морозильной камеры
Equipment: холодильник XXX
Problem: сломана левая петля
Goal: replacement part
Manufacturing target: FDM prototype
```

---

# 8. Guided Capture

## 8.1. Цель

Новичок не обязан заранее понимать:

- какой объектив использовать;
- как влияет wide-angle;
- как поставить свет;
- почему блики вредны;
- почему фон должен быть контрастным;
- почему важна перспектива;
- сколько видов нужно;
- что такое calibration target.

MREA обучает пользователя прямо в процессе съёмки.

## 8.2. Проверки

Приложение оценивает:

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

Примеры сообщений:

```text
✓ Калибровочная поверхность обнаружена
✓ Резкость достаточная
⚠ Блик на правой поверхности
→ Переместите свет левее

⚠ Камера наклонена на 6.8°
→ Выровняйте до ±2°
```

---

# 9. Capture Plan

Для проекта создаётся `CapturePlan`.

Поддерживаемые виды:

- `FRONT`
- `LEFT`
- `RIGHT`
- `TOP`
- `BOTTOM`
- `REAR`
- `DETAIL_A`
- `DETAIL_B`
- `OPTIONAL_3Q`

Система может рекомендовать дополнительные виды.

Она не должна заявлять, что скрытая геометрия восстановлена полностью, если данных недостаточно.

---

# 10. Measurement Mat

## 10.1. Назначение

Печатная рабочая поверхность:

```text
/assets/calibration/
  A4_MEASUREMENT_MAT.pdf
  A3_MEASUREMENT_MAT.pdf
  A2_MEASUREMENT_MAT.pdf
```

На ней:

- координатная сетка;
- миллиметровая разметка;
- ChArUco / ArUco markers;
- контрольные известные расстояния;
- центральные оси;
- рабочая область;
- версия матрицы.

## 10.2. Что даёт

- определение плоскости;
- калибровку;
- коррекцию перспективы;
- масштаб;
- регистрацию нескольких кадров;
- detection смещения камеры;
- единую XY-систему.

## 10.3. Ограничение

Measurement Mat не заменяет физический измерительный инструмент для критических размеров.

Фото используется для:

- topology;
- формы;
- ориентации;
- candidate geometry;
- approximate geometry.

Штангенциркуль используется для:

- verified metric dimensions.

---

# 11. Hands-Free Measurement Session

Это центральная функция продукта.

## 11.1. Физический сценарий

1. Телефон стоит на штативе.
2. Measurement Mat лежит на столе.
3. Деталь находится в рабочей области.
4. Приложение фиксирует положение камеры.
5. Создаётся `CleanReferenceFrame`.
6. Пользователь берёт штангенциркуль.
7. Измеряет feature.
8. Произносит:
   - «замер»;
   - или «замер сорок два восемнадцать».
9. Камера делает кадр.
10. CV пытается определить:
    - инструмент;
    - губки;
    - точки контакта;
    - измеряемый feature.
11. OCR пытается считать дисплей.
12. Voice parser может получить значение.
13. Приложение подтверждает размер.
14. Пользователь выполняет следующий замер.

## 11.2. Источники значения

### A. Direct device
Будущий цифровой канал штангенциркуля.

### B. OCR
Считывание LCD.

### C. Voice
Продиктованное значение.

### D. Manual
Ручная правка после сессии.

## 11.3. Голосовая обратная связь

Высокая уверенность:

```text
— 42,18 миллиметра. Наружный размер. Принято.
```

Низкая уверенность:

```text
— Распознан размер 42,18 миллиметра. Подтвердить?
```

Ответ:

```text
— Да.
```

или:

```text
— Нет. 42,78.
```

---

# 12. Почему кадры не просто накладываются

Простое alpha-compositing measurement frames создаст мусор:

- штангенциркуль перекрывает объект;
- положение рук меняется;
- тени меняются;
- разные кадры создают визуальный шум.

Поэтому:

```text
Measurement Frame
↓
Registration
↓
Caliper detection
↓
Jaw/contact estimation
↓
Value extraction
↓
Feature association
↓
PhysicalMeasurement
```

После этого measurement frame остаётся как evidence.

Финальный view строится поверх чистого reference image.

---

# 13. PhysicalMeasurement

Пример:

```json
{
  "measurement_id": "M001",
  "type": "LINEAR_EXTERNAL",
  "value": 42.18,
  "unit": "mm",
  "uncertainty_mm": 0.02,
  "source": "OCR_MEASURED",
  "confirmed": true,
  "view_id": "FRONT",
  "anchor_a": "EDGE_12",
  "anchor_b": "EDGE_27",
  "evidence_frame_id": "FRAME_001",
  "instrument": {
    "type": "DIGITAL_CALIPER"
  },
  "confidence": 0.97
}
```

---

# 14. Типы измерений

Минимум:

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

---

# 15. Evidence Chain

Каждый verified dimension должен иметь обратную трассировку.

Пример:

```text
CAD Dimension D001
↓
Sketch Dimension D001
↓
PhysicalMeasurement M001
↓
Evidence Frame FRAME_001
↓
Исходная фотография измерения
```

Пользователь нажимает:

```text
42.18
```

и может увидеть:

- источник;
- кадр;
- инструмент;
- confidence;
- дату;
- подтверждение;
- feature.

---

# 16. Computer Vision Pipeline

## 16.1. Capture CV

- blur estimation;
- focus estimation;
- exposure analysis;
- segmentation;
- background removal;
- marker detection;
- image rectification;
- image registration;
- contour extraction.

## 16.2. Geometry CV

- lines;
- circles;
- arcs;
- slot candidates;
- corners;
- centers;
- axes;
- symmetry candidates;
- contour simplification;
- cross-view feature matching later.

## 16.3. Measurement CV

Рискованный исследовательский модуль:

- caliper detection;
- jaw detection;
- contact-region estimation;
- feature association;
- display ROI;
- LCD OCR;
- confidence.

## 16.4. Правило

CV выдаёт candidate.

Candidate не является verified metric truth без physical/user confirmation.

---

# 17. Dimensioned View

Система строит:

```text
Clean Reference Image
+
Geometry Overlay
+
Dimension Lines
+
Physical Measurements
+
Confidence / Provenance
```

Пример:

```text
        ←────── 42.18 ──────→
    ┌──────────────────────────┐
    │        ○        ○        │
    │        ←60.00→           │
    └──────────────────────────┘
```

---

# 18. Semi-Automatic Sketch

## 18.1. Цель

Не генерировать магически готовую 3D-модель.

Цель первой версии:

- создать чистый 2D sketch;
- сохранить topology;
- создать primitives;
- связать реальные размеры;
- добавить constraints;
- отметить inferred elements;
- дать хороший старт в CAD.

## 18.2. Entities

- Point;
- Line;
- Circle;
- Arc;
- Polyline;
- ConstructionLine.

## 18.3. Constraints

- Coincident;
- Horizontal;
- Vertical;
- Parallel;
- Perpendicular;
- Tangent;
- Concentric;
- Equal;
- Symmetric;
- Distance;
- Angle;
- Radius;
- Diameter.

---

# 19. Conflict Policy

Если image-derived geometry конфликтует с verified measurement:

```text
verified measurement wins
```

Если constraint solver не может выполнить verified dimensions:

```text
CONSTRAINT_CONFLICT
```

Система не меняет значение.

---

# 20. SketchPackage

Главный контракт между Geometry и CAD.

Пример:

```json
{
  "sketch_package_version": "1.0",
  "project_id": "P001",
  "part_id": "PART001",
  "view": "FRONT",
  "coordinate_system": "MAT_XY_MM",
  "entities": [],
  "constraints": [],
  "dimensions": [],
  "unresolved": [],
  "source_views": []
}
```

Размер:

```json
{
  "dimension_id": "D001",
  "measurement_id": "M001",
  "value": 42.18,
  "unit": "mm",
  "source": "MANUAL_MEASURED",
  "verified": true
}
```

---

# 21. CAD Bridge

## 21.1. Первый уровень

- SVG;
- DXF;
- JSON SketchPackage.

## 21.2. Дальше

Adapters:

- SOLIDWORKS;
- AutoCAD;
- FreeCAD;
- Fusion / others при необходимости.

## 21.3. SOLIDWORKS

Технологический baseline:

```text
C#
.NET
SOLIDWORKS API
COM
```

## 21.4. Что делает adapter

- принимает SketchPackage;
- создаёт sketch;
- создаёт geometry entities;
- создаёт dimensions;
- создаёт constraints;
- сохраняет связь с `measurement_id`;
- читает итоговый sketch обратно;
- делает VerificationReport.

---

# 22. CAD Verification

До импорта:

```text
M001 = 42.18
M002 = 76.40
M003 = 5.18
```

После создания sketch:

```text
M001 42.18 → 42.180 VERIFIED
M002 76.40 → 76.400 VERIFIED
M003  5.18 →  5.180 VERIFIED
```

Ошибка:

```text
expected = 5.18
actual   = 5.31
status   = MISMATCH
```

Никакого silent correction.

---

# 23. Lifecycle

После CAD начинается физическая жизнь детали.

## 23.1. Revision

```text
PART-0042
REV01
```

## 23.2. Manufacturing Record

- material;
- batch;
- method;
- printer/machine;
- print profile;
- contractor;
- date;
- cost;
- post-processing.

## 23.3. Installation

- date;
- equipment;
- position;
- technician;
- notes.

## 23.4. Test

- test type;
- conditions;
- result;
- photo;
- conclusion.

## 23.5. Failure

- date;
- failure type;
- damage location;
- photos;
- circumstances;
- estimated cause;
- confirmed cause;
- related feature.

Пример:

```text
REV01
PETG
wall = 2.0 mm
fillet = 0.5 mm
→ crack near H2 after 18 days

REV02
PETG
wall = 3.2 mm
fillet = 2.0 mm
→ active, no failures
```

---

# 24. Engineering Knowledge

Со временем MREA должен уметь отвечать:

- какие ревизии ломались;
- какие материалы работали лучше;
- где чаще происходили failure;
- какие geometry changes помогли;
- какие dimensions использовались;
- какой кадр подтверждает конкретный размер;
- какая ревизия стоит на конкретном оборудовании;
- какие решения повторяются в похожих деталях.

---

# 25. AI Policy

AI может:

- классифицировать;
- помогать искать;
- summarise;
- анализировать failure history;
- предлагать candidates;
- помогать с описанием;
- находить похожие кейсы.

AI не может:

- менять verified measurement;
- выдумывать measurement;
- выдавать inferred geometry за measured;
- подтверждать сам себя;
- удалять evidence.

---

# 26. Фотограмметрия

Фотограмметрия — не foundation MVP.

Позже подключается как adapter:

```text
PhotogrammetryProvider
  CaptureSet
      ↓
ReferenceMesh
PointCloud
CameraPoses
```

Reference mesh — дополнительный reference source.

Он не имеет приоритета над verified physical measurements.

---

# 27. Технологическая архитектура

```text
Mobile App
   │
   ├── Camera
   ├── Guided Capture
   ├── Voice
   ├── Annotation Canvas
   └── Offline Session
   │
   ▼
Application API
   │
   ├── Project
   ├── Capture
   ├── Measurement
   ├── Geometry
   ├── Lifecycle
   └── Artifact Registry
   │
   ├──── CV / Geometry Worker
   ├──── Object Storage
   └──── PostgreSQL
   │
   ▼
CAD Adapters
   ├── DXF
   ├── SVG
   ├── SOLIDWORKS
   └── Future adapters
```

---

# 28. Backend Baseline

Предпочтительно:

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- PostgreSQL;
- pytest.

Архитектура:

**modular monolith**.

Микросервисы не нужны на старте.

---

# 29. Mobile Baseline

Кандидат:

- Flutter;
- native bridge для camera/audio/CV при необходимости.

Если camera pipeline окажется слишком ограничен Flutter abstraction:

- допускается Android-first native implementation;
- решение фиксируется ADR.

---

# 30. CV / OCR / Voice Baseline

## CV

- OpenCV;
- готовые segmentation models;
- geometry libraries;
- собственная orchestration logic.

## OCR

Baseline:

- готовый on-device OCR;
- отдельная validation для LCD caliper.

## Voice

Baseline:

- platform speech recognition;
- voice trigger spike;
- offline/latency/false-positive tests.

При необходимости later:

- dedicated keyword spotting.

---

# 31. Domain Model

Минимальный набор:

```text
Project
Part
Equipment
CapturePlan
CaptureSession
CaptureView
CalibrationProfile
MeasurementSession
PhysicalMeasurement
GeometryFeature
Sketch
SketchEntity
SketchConstraint
CADPackage
CADVerificationReport
Revision
ManufacturingRecord
Installation
TestRecord
FailureRecord
EngineeringRule
Artifact
```

---

# 32. Product Matrix

| Горизонтальный слой ↓ / Вертикальный слайс → | Chat 1 Capture | Chat 2 Measurement | Chat 3 Geometry | Chat 4 CAD | Chat 5 Lifecycle |
|---|---|---|---|---|---|
| User Goal | правильно снять деталь | точно зафиксировать размер | построить sketch | перенести и проверить CAD | сопровождать физическую деталь |
| Mobile UI | project/camera/guidance | measurement session | geometry review | export/status | revision/test/failure |
| Domain | Project/Capture | Measurement | Geometry/Sketch | CAD/Verification | Revision/Lifecycle |
| CV | quality/calibration/segmentation | caliper/OCR/anchors | primitives/constraints | CAD comparison | failure image later |
| Backend | project/capture API | measurement API | sketch API | CAD package API | lifecycle API |
| Storage | photos/calibration | measurements/evidence | geometry graph | CAD artifacts | revisions/tests/failures |
| Output | CapturePackage | MeasurementPackage | SketchPackage | VerificationReport | LifecycleState |
| Tests | capture fixtures | measurement fixtures | golden sketches | CAD verification | lifecycle transitions |

---

# 33. Shared Contracts

Shared contracts принадлежат только Integrator.

Базовые:

1. `ProjectContract`
2. `CapturePackage`
3. `MeasurementCaptureFrame`
4. `PhysicalMeasurement`
5. `MeasurementPackage`
6. `SketchPackage`
7. `CADPackage`
8. `CADVerificationReport`
9. `LifecycleEvent`
10. `ArtifactReference`

Каждый контракт версионируется.

---

# 34. Fixture-driven параллельная разработка

Чтобы Chat 2 не ждал Chat 1, создаются fixtures:

```text
/tests/fixtures/contracts/
  project_v1.json
  capture_package_v1.json
  measurement_package_v1.json
  sketch_package_v1.json
  cad_verification_v1.json
  lifecycle_event_v1.json
```

Каждый чат обязан:

- читать upstream fixture;
- выдавать downstream fixture;
- проходить contract tests.

---

# 35. CHAT 1 — PROJECT & GUIDED CAPTURE

## Ownership

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
- `CapturePackage`.

## Не отвечает за

- смысл measurement;
- final measurement value;
- final OCR semantics;
- sketch;
- CAD;
- lifecycle.

## Основные компоненты

```text
ProjectService
CapturePlanService
CameraSession
ImageQualityAnalyzer
CalibrationDetector
CaptureRegistration
ReferenceFrameBuilder
VoiceCaptureTrigger
CapturePackageBuilder
```

## MVP

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

## Acceptance Criteria

- project создаётся и восстанавливается;
- FRONT view завершается;
- clean frame отделён от measurement frames;
- calibration сохраняется;
- frame имеет timestamp + camera metadata;
- voice trigger создаёт capture event;
- CapturePackage проходит schema validation.

---

# 36. CHAT 2 — PHYSICAL MEASUREMENT

## Ownership

Chat 2 отвечает за:

- MeasurementSession;
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
- `MeasurementPackage`.

## Не отвечает за

- camera core;
- final sketch;
- CAD;
- lifecycle.

## Компоненты

```text
MeasurementSessionService
MeasurementTypeRegistry
FeatureAnchorSelector
CaliperDetector
CaliperJawEstimator
DisplayRoiDetector
OcrMeasurementReader
VoiceMeasurementParser
MeasurementConfirmation
MeasurementEvidenceService
MeasurementPackageBuilder
```

## Реализация по сложности

### Phase A
Manual anchors + manual value.

### Phase B
Snap к detected features.

### Phase C
OCR proposes value.

### Phase D
Voice proposes/confirms value.

### Phase E
Automatic caliper/jaw/contact estimation.

## Acceptance Criteria

- every PhysicalMeasurement has provenance;
- verified measurement has evidence or explicit confirmation;
- OCR cannot silently become verified;
- evidence frame можно открыть;
- measurement связан с view + anchors;
- MeasurementPackage валиден.

---

# 37. CHAT 3 — GEOMETRY & SEMI-AUTOMATIC SKETCH

## Ownership

Chat 3 отвечает за:

- GeometryFeature model;
- contour extraction;
- line/circle/arc primitives;
- GeometryGraph;
- constraints;
- binding measurements;
- conflict detection;
- dimensioned view;
- `SketchPackage`.

## Не отвечает за

- camera;
- OCR;
- CAD-native API;
- lifecycle.

## Компоненты

```text
GeometryFeatureExtractor
PrimitiveDetector
GeometryGraph
ConstraintCandidateEngine
ConstraintResolver
DimensionBinder
GeometryConflictDetector
DimensionedViewRenderer
SketchPackageBuilder
```

## Закон

```text
verified measurement > image-derived estimate
```

## Acceptance Criteria

- простой FRONT fixture превращается в SketchPackage;
- line/circle/arc поддерживаются;
- dimensions имеют measurement_id;
- одинаковый fixture → deterministic output;
- golden tests проходят;
- inferred geometry отличается от measured.

---

# 38. CHAT 4 — CAD BRIDGE & VERIFICATION

## Ownership

Chat 4 отвечает за:

- SVG/DXF;
- CAD adapter interface;
- SOLIDWORKS adapter;
- creation of sketch;
- CAD dimensions;
- measurement mapping;
- read-back;
- VerificationReport;
- CAD integration tests.

## Не отвечает за

- capture;
- measurement extraction;
- geometry semantics;
- lifecycle.

## SOLIDWORKS baseline

```text
C#
.NET
SOLIDWORKS API
COM
```

## Verification status

- `VERIFIED`
- `MISMATCH`
- `MISSING`
- `CONSTRAINT_CONFLICT`

## Acceptance Criteria

Golden fixture:

```text
80.20 → 80.200 VERIFIED
42.10 → 42.100 VERIFIED
5.10  → 5.100 VERIFIED
60.00 → 60.000 VERIFIED
```

Ни один mismatch не скрывается.

---

# 39. CHAT 5 — LIFECYCLE & ENGINEERING KNOWLEDGE

## Ownership

Chat 5 отвечает за:

- revisions;
- manufacturing records;
- installation;
- tests;
- failures;
- revision comparison;
- field status;
- equipment mapping;
- lifecycle timeline;
- engineering knowledge queries.

## Не отвечает за

- camera;
- measurement;
- sketch;
- SolidWorks API.

## Компоненты

```text
RevisionService
ManufacturingService
InstallationService
TestService
FailureService
RevisionComparison
EquipmentPartRegistry
LifecycleTimeline
KnowledgeQueryService
```

## Acceptance Criteria

Поддерживается:

```text
REV01
→ manufactured
→ installed
→ failed
→ failure evidence
→ REV02
→ manufactured
→ installed
→ active
```

---

# 40. INTEGRATOR / MAIN CHAT

## Ownership

Integrator утверждает:

- shared contracts;
- global architecture;
- repository structure;
- ownership;
- cross-slice dependencies;
- release gates;
- ADR;
- contract migrations.

## Ведёт документы

```text
PRODUCT_CONCEPT.md
ARCHITECTURE.md
SLICE_MATRIX.md
CONTRACTS.md
DECISIONS.md
INTEGRATION_STATE.md
ROADMAP.md
```

На старте текущий SSOT заменяет их.

## Change Request format

```text
CHANGE_REQUEST

Requester:
Contract:
Problem:
Current behavior:
Requested change:
Reason:
Affected chats:
Backward compatible: YES/NO
Migration:
```

---

# 41. Ownership файлов

После появления repository:

```text
/apps/mobile/capture/              CHAT 1
/apps/mobile/measurement/          CHAT 2
/core/geometry/                    CHAT 3
/adapters/cad/                     CHAT 4
/core/lifecycle/                   CHAT 5

/core/contracts/                   INTEGRATOR
/core/domain/shared/               INTEGRATOR
/tests/fixtures/contracts/         INTEGRATOR
/docs/architecture/                INTEGRATOR
```

Никто не меняет чужую директорию без явного интеграционного решения.

---

# 42. Build / Reuse Check

Перед реализацией нетривиальной функции чат обязан заполнить:

```text
BUILD / REUSE CHECK

Проблема:
Есть ли готовое open-source решение:
Можно ли использовать: YES / NO / PARTIAL
Что используем:
Что пишем сами:
Почему:
Lock-in risk:
Fallback:
```

---

# 43. Предлагаемая структура repository

Это **концептуальное предложение**, а не приказ создавать её поверх существующего проекта.

Если реальный repository уже существует, он является source of truth.

```text
mrea/
├─ apps/
│  ├─ mobile/
│  │  ├─ capture/
│  │  ├─ measurement/
│  │  ├─ geometry_review/
│  │  └─ lifecycle/
│  └─ api/
│
├─ core/
│  ├─ contracts/
│  ├─ project/
│  ├─ capture/
│  ├─ measurement/
│  ├─ geometry/
│  ├─ lifecycle/
│  └─ artifacts/
│
├─ workers/
│  └─ vision/
│
├─ adapters/
│  ├─ storage/
│  ├─ speech/
│  ├─ ocr/
│  └─ cad/
│     ├─ dxf/
│     ├─ svg/
│     └─ solidworks/
│
├─ tests/
│  ├─ fixtures/
│  │  └─ contracts/
│  ├─ unit/
│  ├─ integration/
│  └─ golden/
│
├─ assets/
│  └─ calibration/
│
└─ docs/
```

---

# 44. Golden End-to-End Flow

Первая интегрированная версия обязана пройти один реальный простой кейс.

## Деталь

Плоская деталь:

- внешний контур;
- два отверстия;
- один radius;
- одна thickness.

## Capture

```text
FRONT
SIDE
TOP
```

## Measurements

```text
width       = 80.20 mm
height      = 42.10 mm
hole_diam   = 5.10 mm
center_dist = 60.00 mm
thickness   = 3.20 mm
```

## Sketch

Создаётся FRONT sketch.

## CAD

Импорт в SOLIDWORKS.

## Verification

Все verified measurements совпадают в tolerance.

## Physical

Печатается prototype.

## Lifecycle

```text
REV01
MANUFACTURED
INSTALLED
TESTED
```

---

# 45. Roadmap

## R0 — Contracts & Fixtures

- contracts v1;
- fixtures;
- repository;
- CI;
- ownership map.

## R1 — Capture Baseline

- project;
- camera;
- calibration mat;
- clean frame;
- manual measurement frames.

## R2 — Manual Measurement Baseline

- annotation;
- manual numeric input;
- provenance;
- evidence;
- dimensioned view.

На этом этапе продукт уже должен быть полезным.

## R3 — Semi-Automatic Geometry

- contours;
- primitives;
- snapping;
- SketchPackage;
- DXF/SVG.

## R4 — Hands-Free

- voice trigger;
- voice value;
- OCR experiments;
- caliper/jaw experiments.

## R5 — SOLIDWORKS Integration

- C# adapter;
- sketch creation;
- dimensions;
- verification.

## R6 — Lifecycle

- revisions;
- manufacturing;
- install;
- test;
- failure.

## R7 — Multi-View Geometry

- view relationships;
- advanced alignment;
- cross-view feature matching.

## R8 — Photogrammetry Adapter

- ReferenceMesh;
- CameraPoses;
- PointCloud.

## R9 — Engineering Knowledge & AI

- semantic search;
- similar parts;
- failure analysis;
- revision explanations;
- recommendation candidates.

---

# 46. Testing Strategy

## Unit

Каждый domain component.

## Contract

Каждый межслайсовый JSON/schema contract.

## Golden Geometry

Input fixture → exact expected sketch.

## Image Fixtures

Набор:

- good;
- blur;
- glare;
- perspective;
- partial marker;
- bad background.

## OCR Dataset

Собственный dataset LCD штангенциркуля:

- разные числа;
- углы;
- свет;
- glare;
- разные модели later.

## Physical Tests

Critical geometry должна проверяться физически.

---

# 47. Offline-first

Measurement workflow может происходить:

- в мастерской;
- на складе;
- на площадке;
- без интернета.

Поэтому capture/measurement должны:

- сохранять session локально;
- не терять frames;
- поддерживать basic calibration локально;
- синхронизировать позже.

Cloud-only capture запрещён как архитектурная зависимость.

---

# 48. Privacy / Deployment

Продукт может содержать:

- proprietary parts;
- CAD;
- фото оборудования;
- внутренние инженерные данные.

Архитектура должна допускать:

- local-only;
- self-hosted backend;
- отключение внешнего AI;
- configurable providers.

---

# 49. Технические риски

## High

1. Reliable caliper jaw/contact detection.
2. LCD OCR в реальных условиях.
3. Cross-view correspondence.
4. Constraint-consistent sketch generation.
5. Robust SolidWorks import/constraints.

## Medium

1. Segmentation.
2. Marker calibration.
3. Perspective correction.
4. Primitive detection.
5. Voice trigger.

## Low

1. Project model.
2. Revision model.
3. Evidence storage.
4. Manual measurement annotation.
5. REST API.

Roadmap не должен начинаться с High-risk задач.

---

# 50. Первая реально полезная версия

Первый usable release может вообще не понимать штангенциркуль визуально.

Он уже полезен, если:

1. создаёт project;
2. ведёт guided capture;
3. делает clean views;
4. помогает быстро привязать размер к feature;
5. пользователь вводит число;
6. хранится evidence;
7. создаётся dimensioned sheet;
8. формируется SketchPackage;
9. есть DXF/SVG;
10. можно вести REV01 → REV02.

После этого постепенно автоматизируются:

- voice;
- OCR;
- caliper detection;
- photogrammetry.

---

# 51. Главная архитектурная формула

```text
PHYSICAL PART
     ↓
GUIDED CAPTURE
     ↓
PHYSICAL MEASUREMENT
     ↓
TRACEABLE GEOMETRY
     ↓
SEMI-AUTOMATIC SKETCH
     ↓
CAD VERIFICATION
     ↓
MANUFACTURING
     ↓
FIELD TEST
     ↓
REVISION
     ↓
ENGINEERING KNOWLEDGE
```

---

# 52. Главная продуктовая формула

MREA — это не:

> «Сфотографируй деталь, и AI угадает CAD».

MREA — это:

> **система, где каждая важная цифра и геометрическая сущность имеет известное происхождение, а инженер может пройти от CAD-размера назад до физического измерения и исходного кадра.**

---

# 53. Команды запуска чатов

## Chat 1

> Ты Chat 1 проекта MREA. Этот SSOT — источник истины. Твой ownership: Project & Guided Capture. Восстанови контекст, перечисли входные/выходные контракты, затем реализуй свой vertical slice. Shared contracts не меняй. Если контракт недостаточен — Change Request. Используй fixtures и не жди другие чаты.

## Chat 2

> Ты Chat 2 проекта MREA. Этот SSOT — источник истины. Твой ownership: Physical Measurement. Начни с manual measurement baseline, потом snapping/OCR/voice. Caliper CV не должен блокировать MVP. Shared contracts не менять без Change Request.

## Chat 3

> Ты Chat 3 проекта MREA. Этот SSOT — источник истины. Твой ownership: Geometry & Semi-Automatic Sketch. Работай от fixtures CapturePackage + MeasurementPackage. Verified measurement всегда выше vision estimate. Реализуй deterministic SketchPackage и golden tests.

## Chat 4

> Ты Chat 4 проекта MREA. Этот SSOT — источник истины. Твой ownership: CAD Bridge & Verification. Сначала generic SketchPackage→DXF/SVG, затем SOLIDWORKS C# adapter. Все verified measurements обязаны пройти CAD read-back verification.

## Chat 5

> Ты Chat 5 проекта MREA. Этот SSOT — источник истины. Твой ownership: Lifecycle & Engineering Knowledge. Реализуй revision/manufacturing/install/test/failure flow независимо через fixtures. AI не внедрять раньше структурированной lifecycle-модели.

## Integrator

> Ты Integrator проекта MREA. Этот SSOT — источник истины. Твоя задача — contracts, architecture, ownership, integration, ADR, fixtures, release gates. Не реализуй функциональность за соседние чаты без необходимости. Любое cross-slice изменение должно быть формализовано.

---

# 54. Формат отчёта каждого чата

После итерации каждый чат возвращает:

```text
IMPLEMENTATION_REPORT

1. Что реализовано
2. Какие исходные contracts использованы
3. Какие файлы изменены/добавлены
4. Какие зависимости добавлены
5. Какие тесты добавлены
6. Какие тесты прошли
7. Что не проверено
8. Известные ограничения
9. Новые технические знания
10. Change Requests
11. Что готово к интеграции
```

---

# 55. Definition of Done слайса

Slice считается done только если:

- пользовательский сценарий работает;
- domain model есть;
- persistence/API есть, если нужны;
- upstream contract читается;
- downstream contract создаётся;
- contract tests проходят;
- fixtures валидны;
- ошибки не скрываются;
- documentation обновлена;
- чужие ownership-модули не затронуты;
- нет незадокументированных временных workaround.

---

# 56. Финальное правило проекта

**Собственный продукт — да.  
Собственный workflow, данные, проверяемость и инженерная логика — обязательно.  
Повторная реализация уже решённой низкоуровневой задачи без причины — нет.**

Стандартные технологии используются как строительные блоки.

Уникальность MREA находится в:

- measured truth;
- provenance;
- evidence;
- hands-free workflow;
- geometry traceability;
- CAD verification;
- lifecycle feedback loop;
- engineering memory.
