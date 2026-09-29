# Chat 3 — Geometry & Semi-Automatic Sketch

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 3  
**Vertical slice:** Geometry & Semi-Automatic Sketch  
**Источник истины:** пользовательский SSOT `MREA_SSOT_PRODUCT_CONCEPT_ARCHITECTURE_CHAT_ROLES_V0_1_2026-09-29.md`  
**Статус документа:** актуализирован при подключении Chat 3 к repository  
**Дата:** 2026-09-29

---

## 1. Назначение роли

Chat 3 преобразует подтверждённые downstream-данные Capture/Measurement в трассируемое геометрическое представление и deterministic `SketchPackage`, пригодный для последующего CAD Bridge.

Основная задача слайса — не «угадать CAD», а построить проверяемую 2D-геометрию, где:

- image-derived geometry остаётся candidate/inferred до подтверждения;
- verified physical measurements имеют приоритет над vision estimates;
- каждый dimension сохраняет связь с исходным `measurement_id`;
- конфликт не скрывается и не исправляется молча;
- одинаковый входной fixture даёт одинаковый результат.

---

## 2. Ownership

Chat 3 отвечает за:

- `GeometryFeature` model;
- contour extraction;
- line/circle/arc primitives;
- `GeometryGraph`;
- constraint candidates;
- constraint resolution внутри своего слайса;
- binding measurements к geometry entities/features;
- geometry/measurement conflict detection;
- dimensioned view;
- формирование `SketchPackage`.

### Основные компоненты

- `GeometryFeatureExtractor`
- `PrimitiveDetector`
- `GeometryGraph`
- `ConstraintCandidateEngine`
- `ConstraintResolver`
- `DimensionBinder`
- `GeometryConflictDetector`
- `DimensionedViewRenderer`
- `SketchPackageBuilder`

---

## 3. Что не входит в ownership Chat 3

Chat 3 не отвечает за:

- camera core;
- Guided Capture;
- Measurement Mat capture/calibration ownership;
- OCR;
- voice measurement semantics;
- final physical measurement confirmation;
- caliper/jaw/contact detection;
- CAD-native API;
- SOLIDWORKS adapter;
- CAD read-back verification;
- lifecycle/revisions/manufacturing/failures.

Chat 3 не изменяет самостоятельно:

- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- shared contract schemas;
- global architecture;
- ownership других chats.

Эти области принадлежат Integrator.

---

## 4. Входы

Основные upstream contracts по SSOT:

- `CapturePackage`;
- `MeasurementPackage`;
- `PhysicalMeasurement` как элемент/связанная сущность measurement data;
- artifact/view references, если они включены в утверждённые contracts.

Рабочая формула:

```text
CapturePackage
      +
MeasurementPackage
      ↓
Geometry & Sketch pipeline
```

Chat 3 должен работать от canonical fixtures и не обязан ждать runtime-реализацию Chat 1/Chat 2.

---

## 5. Выход

Основной downstream output:

`SketchPackage`

Минимально ожидаемые категории данных, определённые SSOT:

- `sketch_package_version`;
- project/part identity;
- view;
- coordinate system;
- geometry entities;
- constraints;
- dimensions;
- unresolved/conflicts;
- source views.

Dimension должен сохранять:

- `dimension_id`;
- `measurement_id`;
- value/unit;
- source/provenance;
- verified state.

Точная canonical schema не определяется Chat 3 самостоятельно.

---

## 6. Главный метрологический инвариант

```text
verified physical measurement > image-derived estimate
```

Следствия:

1. Vision/geometry estimate не может молча заменить verified measurement.
2. Если geometry невозможно согласовать с verified dimension, создаётся явный conflict.
3. Solver не имеет права «подправить» физический размер ради замыкания эскиза.
4. Inferred geometry должна быть отличима от measured/confirmed geometry.
5. Evidence/provenance chain не должна теряться при переходе к `SketchPackage`.

---

## 7. Geometry pipeline

Базовый поток Chat 3:

```text
Clean Reference / normalized view
            +
Physical Measurements
            ↓
Contour Extraction
            ↓
Primitive Detection
            ↓
Geometry Features
            ↓
GeometryGraph
            ↓
Constraint Candidates
            ↓
Measurement Binding
            ↓
Conflict Detection
            ↓
Constraint Resolution
            ↓
Dimensioned View
            ↓
SketchPackage
```

Порядок может уточняться внутренне, но observable contract и метрологические правила должны сохраняться.

---

## 8. Primitive baseline

Первая обязательная поддержка:

- `Point` при необходимости внутренней topology;
- `Line`;
- `Circle`;
- `Arc`;
- `Polyline`/`ConstructionLine` только когда потребуются утверждённым кейсом.

Acceptance SSOT явно требует минимум:

- line;
- circle;
- arc.

Первый golden FRONT fixture должен быть достаточно простым, чтобы проверить topology, measurement binding и deterministic output независимо от advanced CV.

---

## 9. Constraint baseline

SSOT перечисляет целевые constraints:

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

Не все constraints обязаны появиться в первой внутренней итерации одновременно.

Приоритет первой реализации:

1. topology-preserving constraints;
2. очевидные deterministic geometric relations;
3. dimension constraints, связанные с verified measurements;
4. явное unresolved/conflict состояние вместо агрессивного inference.

---

## 10. GeometryGraph

`GeometryGraph` — внутренняя модель связей между entities/features и measurement anchors.

Он должен позволять минимум:

- хранить стабильные entity/feature identifiers;
- связывать primitives между собой;
- связывать measurement anchors с geometry;
- представлять candidate constraints;
- отличать detected/derived/inferred/confirmed происхождение;
- находить конфликтующие связи;
- строить deterministic downstream representation.

Точная внутренняя структура графа принадлежит Chat 3 до тех пор, пока она не становится shared contract.

---

## 11. Measurement binding

`DimensionBinder` обязан связывать sketch dimension с исходным `measurement_id`.

Запрещено создавать verified dimension, если отсутствует достаточная upstream информация о verified physical measurement.

Если геометрический feature найден vision-алгоритмом, а physical measurement указывает иной метрический размер:

```text
physical verified value wins
```

Vision estimate сохраняется только как diagnostic/candidate information, если такая информация предусмотрена внутренней моделью или утверждённым contract.

---

## 12. Conflict policy

Минимальные конфликтные состояния:

- geometry estimate vs verified measurement;
- incompatible verified dimensions;
- unsatisfied constraint set;
- missing geometry anchor для verified dimension;
- ambiguous primitive/feature binding.

SSOT задаёт `CONSTRAINT_CONFLICT` как обязательный явный результат при невозможности solver выполнить verified dimensions.

Никакой silent correction не допускается.

---

## 13. Dimensioned View

Dimensioned view строится как производное представление:

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

Он не заменяет исходные evidence frames и не становится новым метрологическим источником истины.

---

## 14. Determinism

Одинаковый canonical fixture должен приводить к одинаковому `SketchPackage`.

Для этого реализация должна исключать необоснованную недетерминированность в:

- entity ordering;
- generated identifiers;
- candidate ordering;
- constraint ordering;
- floating-point normalization/serialization;
- tie-breaking при одинаковых candidates.

Если алгоритм использует вероятностный CV/ML-компонент, golden layer должен получать стабилизированный/зафиксированный вход либо явно нормализовать его до deterministic contract output.

---

## 15. Golden case

Глобальный SSOT определяет первый end-to-end кейс как плоскую деталь с:

- внешним контуром;
- двумя отверстиями;
- одним radius;
- одной thickness.

Для FRONT geometry baseline релевантны размеры:

- width = 80.20 mm;
- height = 42.10 mm;
- hole_diam = 5.10 mm;
- center_dist = 60.00 mm.

Thickness относится к другому view/physical property и не должна искусственно встраиваться в FRONT sketch без утверждённой cross-view модели.

Первый Chat 3 golden test должен доказать:

- построение простого FRONT sketch;
- line/circle/arc support;
- measurement binding;
- deterministic serialization;
- явное различие measured и inferred geometry.

---

## 16. Roadmap position

Глобальный roadmap связывает основной Chat 3 slice с:

### R3 — Semi-Automatic Geometry

- contours;
- primitives;
- snapping;
- `SketchPackage`;
- downstream DXF/SVG через Chat 4.

### R7 — Multi-View Geometry

Позднее расширение:

- view relationships;
- advanced alignment;
- cross-view feature matching.

R7 не должен блокировать первый FRONT-only R3 baseline.

---

## 17. Acceptance Criteria

Согласно SSOT, Chat 3 считается прошедшим локальные критерии, когда:

- простой FRONT fixture превращается в `SketchPackage`;
- line/circle/arc поддерживаются;
- dimensions имеют `measurement_id`;
- одинаковый fixture даёт deterministic output;
- golden tests проходят;
- inferred geometry отличается от measured.

Общий Definition of Done дополнительно требует:

- upstream contract читается;
- downstream contract создаётся;
- contract tests проходят;
- fixtures валидны;
- ошибки не скрываются;
- documentation обновлена;
- чужие ownership-модули не затронуты;
- нет незадокументированных временных workaround.

---

## 18. Build / Reuse baseline

Перед нетривиальной реализацией заполняется `BUILD / REUSE CHECK`.

Исходный SSOT разрешает/ожидает использование готовых строительных блоков:

- OpenCV для CV/contour/geometry-related primitives, где применимо;
- готовых geometry libraries;
- существующего geometry/constraint solver, если он удовлетворяет требованиям.

Chat 3 пишет самостоятельно:

- MREA-specific geometry orchestration;
- `GeometryGraph` semantics;
- provenance-aware measurement binding;
- conflict policy;
- deterministic SketchPackage assembly;
- golden normalization/verification rules.

Конкретная сторонняя geometry/solver dependency пока не выбрана. Она должна быть подтверждена отдельным Build / Reuse Check до добавления в код.

---

## 19. Технические риски

### High

- constraint-consistent sketch generation.

### Medium

- primitive detection robustness;
- contour simplification;
- geometry candidate ambiguity.

### Later / cross-slice

- cross-view correspondence;
- advanced multi-view alignment.

Рискованный advanced solver/CV не должен блокировать deterministic fixture-driven baseline.

---

## 20. Ограничения разработки

1. Не выдумывать shared schemas.
2. Не менять verified physical measurements.
3. Не превращать vision estimate в verified metric truth.
4. Не реализовывать CAD-native semantics вместо Chat 4.
5. Не затрагивать чужие ownership directories.
6. Не начинать с multi-view/photogrammetry, пока не закрыт простой FRONT vertical slice.
7. Не скрывать ambiguous/unresolved/conflict состояния.
8. Не связывать correctness только с визуально «похожим» sketch — важны topology, dimensions, provenance и deterministic contract output.

---

## 21. Change Request к Integrator

```text
CHANGE_REQUEST

Requester:
Chat 3 — Geometry & Semi-Automatic Sketch

Contract:
CapturePackage
PhysicalMeasurement
MeasurementPackage
SketchPackage
ArtifactReference (если используется для dimensioned view/source views)

Problem:
SSOT определяет назначение, пример полей и ownership contracts,
но repository пока не содержит canonical versioned schemas/fixtures.

Current behavior:
Есть концептуальные contract names и SketchPackage example,
но нет утверждённых machine-validatable v1 schemas.

Requested change:
Утвердить canonical v1 schemas и fixtures, необходимые Chat 3, включая:
- CapturePackage view/reference representation;
- MeasurementPackage structure;
- PhysicalMeasurement anchors/provenance/verified semantics;
- SketchPackage entity model;
- SketchPackage constraint model;
- dimension representation с measurement_id;
- unresolved/conflict representation;
- coordinate-system representation;
- stable ID policy;
- ArtifactReference, если нужен для rendered dimensioned view.

Также предоставить canonical FRONT golden upstream fixture,
который может быть использован независимо от runtime Chat 1/Chat 2.

Reason:
Без canonical v1 contracts Chat 3 может реализовать внутренний geometry core,
но не может честно гарантировать совместимость upstream/downstream
или выполнить contract Definition of Done.

Affected chats:
Integrator
Chat 2
Chat 3
Chat 4

Backward compatible:
YES — canonical contracts отсутствуют в текущем repository.

Migration:
Not applicable at current repository state.
```

---

## 22. План реализации после Integrator baseline

1. Повторно проверить актуальное дерево repository и ownership.
2. Прочитать canonical `CapturePackage`/`MeasurementPackage` fixtures.
3. Проверить `PhysicalMeasurement` semantics и anchor representation.
4. Провести Build / Reuse Check для contour/primitive/constraint dependencies.
5. Реализовать внутреннюю geometry domain model.
6. Реализовать deterministic primitive baseline для line/circle/arc.
7. Реализовать `GeometryGraph`.
8. Реализовать measurement binding.
9. Реализовать conflict detection.
10. Реализовать минимальный constraint resolution baseline.
11. Сформировать canonical `SketchPackage`.
12. Добавить FRONT golden tests и determinism tests.
13. Добавить dimensioned view renderer после стабилизации geometry data.
14. Обновить `IMPLEMENTATION_STATE.md` и Implementation Report.

---

## 23. Текущий статус

На момент создания документа product code и canonical shared contracts в repository отсутствуют. Поэтому выполнена только безопасная организационная и архитектурная инициализация Chat 3. Никаких shared schemas, чужих modules или глобальной структуры Chat 3 не изменял.
