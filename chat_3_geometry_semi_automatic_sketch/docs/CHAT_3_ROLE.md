# Chat 3 — Geometry & Semi-Automatic Sketch

**Проект:** MREA — Measured Reverse Engineering Assistant  
**Роль:** Chat 3  
**Vertical slice:** Geometry & Semi-Automatic Sketch  
**Источник истины:** repository `main` → `core/contracts/` → canonical fixtures → product SSOT  
**Active directive:** `OD-2026-09-29-001`  
**Ring:** 1  
**Дата актуализации:** 2026-09-29

---

## 1. Назначение роли

Chat 3 преобразует canonical Capture/Measurement data и geometry candidates в трассируемое 2D geometric representation и deterministic `SketchPackage v1`, пригодный для downstream CAD Bridge.

Основная задача — не «угадать CAD», а построить проверяемую геометрию, где:

- verified physical measurements имеют приоритет над vision/geometry estimates;
- каждый published dimension сохраняет `measurement_id`;
- ambiguous/conflicting geometry не скрывается;
- одинаковый canonical input даёт одинаковый canonical output;
- Chat 3 не переопределяет shared contracts.

---

## 2. Ownership

Chat 3 отвечает за:

- internal geometry domain model;
- `POINT`, `LINE`, `CIRCLE`, `ARC` v1 support;
- contour/primitive extraction boundary;
- `GeometryGraph`;
- constraint candidates и последующий constraint resolution внутри slice;
- anchor/feature → geometry association;
- measurement binding;
- geometry-vs-measurement conflict detection;
- dimensioned view;
- deterministic `SketchPackageBuilder`;
- golden/determinism tests своего slice.

Текущие компоненты:

- `CanonicalInputAdapter`;
- `GeometryGraph`;
- `AnchorEntityMatcher`;
- `ConstraintCandidateEngine`;
- `DimensionBinder`;
- `GeometryConflictDetector`;
- `GeometryPipeline`;
- `SketchPackageBuilder`.

Будущие компоненты внутри ownership:

- `GeometryFeatureExtractor`;
- `PrimitiveDetector`;
- `ConstraintResolver`;
- `DimensionedViewRenderer`.

---

## 3. Что не входит в ownership Chat 3

Chat 3 не отвечает за:

- camera core и Guided Capture;
- Measurement Mat capture/calibration ownership;
- OCR/voice measurement semantics;
- final physical measurement confirmation;
- caliper/jaw/contact detection;
- CAD-native API / SOLIDWORKS adapter;
- CAD read-back verification;
- lifecycle/revisions/manufacturing/failures.

Chat 3 не изменяет самостоятельно:

- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- global architecture;
- ownership других chats.

Эти области принадлежат Chat 6 / Integrator либо соответствующему slice owner.

---

## 4. Canonical входы

После публикации baseline Chat 6 canonical inputs определены:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/capture_package_v1.json`;
- `tests/fixtures/contracts/measurement_package_v1.json`.

Рабочий поток:

```text
CapturePackage v1
      +
MeasurementPackage v1
      ↓
CanonicalInputAdapter
      ↓
Chat 3 internal geometry domain
```

Для текущего FRONT acceptance target:

```text
coordinate_system = MAT_XY_MM
```

Canonical measurement anchors могут содержать `feature_id`; Chat 3 использует его как primary semantic binding hint, а coordinate-distance matching — как fallback.

---

## 5. Canonical выход

Основной output:

`SketchPackage v1`

Golden output fixture:

`tests/fixtures/contracts/sketch_package_v1.json`

Published package содержит:

- `schema_version`;
- `sketch_package_id`;
- project/part/view identity;
- `MAT_XY_MM` coordinate system;
- geometry entities;
- constraints;
- dimensions;
- unresolved items;
- source view ids.

Dimension сохраняет:

- `dimension_id`;
- `measurement_id`;
- type;
- value/unit;
- entity ids;
- verified state;
- provenance.

Chat 3 не определяет форму этого wire contract самостоятельно — builder обязан соответствовать Integrator-owned schema.

---

## 6. Главный метрологический инвариант

```text
verified physical measurement > image-derived / geometry-derived estimate
```

Следствия:

1. Geometry estimate не может молча заменить verified value.
2. Conflict становится explicit diagnostic/unresolved state.
3. Solver не имеет права «подправить» verified physical dimension ради красивого sketch.
4. Vision/derived geometry остаётся отличимой по provenance.
5. Evidence/measurement traceability сохраняется через `measurement_id`.

---

## 7. Текущий Ring 1 pipeline

```text
CapturePackage v1
        +
MeasurementPackage v1
        ↓
CanonicalInputAdapter
        ↓
normalized MeasurementRef + feature hints
        +
primitive candidates
        ↓
GeometryGraph
        ↓
AnchorEntityMatcher
        ↓
DimensionBinder
        ↓
geometry estimate
        ↓
GeometryConflictDetector
        +
ConstraintCandidateEngine
        ↓
GeometryDraft (internal)
        ↓
SketchPackageBuilder
        ↓
SketchPackage v1
        ↓
JSON Schema validation + exact golden comparison
```

`GeometryDraft` остаётся internal representation и не является shared contract.

---

## 8. Primitive baseline

Canonical v1 mandatory vocabulary:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Все четыре типа поддерживаются internal model и canonical serializer.

Расширение vocabulary (`POLYLINE`, `CONSTRUCTION_LINE` и т. п.) — только после Change Request/новой директивы Integrator.

Raw image primitive detection пока не реализован; текущий FRONT acceptance использует deterministic internal detector-output fixture.

---

## 9. GeometryGraph

`GeometryGraph` — internal deterministic topology representation.

Ring 1 поддерживает:

- stable entity ids;
- duplicate-id rejection;
- point incidence;
- line endpoint incidence;
- arc endpoint incidence;
- deterministic adjacency ordering.

Circle не имеет endpoint incidence и участвует в других geometry/measurement relations.

---

## 10. Measurement binding

`DimensionBinder` связывает canonical measurements с geometry entities.

Binding policy Ring 1:

1. exact unique `feature_id` match, если canonical anchor его содержит;
2. coordinate-distance fallback;
3. ambiguous/out-of-range association → explicit unresolved;
4. никакой fabricated verified dimension при отсутствии достаточной связи.

Поддерживаемые geometry estimates Ring 1:

- diameter для circle;
- radius для circle/arc;
- center distance для двух circles;
- linear/thickness/slot width для параллельных lines.

---

## 11. Constraint baseline

Internal candidate engine поддерживает:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`;
- `CONCENTRIC`;
- `EQUAL`.

Canonical schema также допускает другие constraints, но Ring 1 их не генерирует.

Текущий canonical FRONT golden fixture содержит пустой `constraints`, поэтому purely inferred candidates остаются internal и не публикуются в `SketchPackage v1` без отдельной promotion policy.

General `ConstraintResolver` ещё не реализован.

---

## 12. Conflict policy

Ring 1 явно различает:

- unresolved/ambiguous anchor binding;
- verified measurement vs derived geometry mismatch.

Verified value сохраняется неизменным.

Internal geometry conflict преобразуется builder-ом в canonical `unresolved` item, а не исправляется молча.

Будущие обязательные состояния:

- incompatible verified dimensions;
- unsatisfied constraint set;
- `CONSTRAINT_CONFLICT` при невозможности удовлетворить verified dimensions.

---

## 13. Determinism

Одинаковый canonical input должен давать одинаковый `SketchPackage`.

Ring 1 стабилизирует:

- entity ordering;
- dimension ordering;
- graph adjacency;
- constraint candidate ordering;
- association tie-breaking;
- generated canonical dimension ids.

Acceptance test дополнительно меняет primitive input order и требует идентичный canonical output.

---

## 14. Golden FRONT case

Текущий canonical baseline:

- width = `80.20 mm`;
- height = `42.10 mm`;
- hole diameter = `5.10 mm`;
- center distance = `60.00 mm`;
- два circle holes;
- rectangular outer contour.

Thickness относится к другому view/physical property и не встраивается искусственно в FRONT sketch.

Canonical measurement ids:

- `M-WIDTH`;
- `M-HEIGHT`;
- `M-HOLE`;
- `M-CENTER`.

Все они должны сохраняться в canonical dimensions.

---

## 15. Ring 1 acceptance

Добавлены проверки:

- exact equality с `sketch_package_v1.json`;
- Draft 2020-12 JSON Schema validation;
- deterministic result при reversed primitive order;
- сохранение canonical `measurement_id` links;
- schema-valid `POINT` support.

Phase 1 historical runtime verification:

```text
6 passed in 0.06s
```

Phase 2 runtime gate в текущем ChatGPT sandbox не выполнен из-за отсутствия checkout/network path к GitHub. Это ограничение честно зафиксировано; Phase 2 не помечается как passed без запуска.

Current handoff status:

```text
READY_FOR_INTEGRATOR_RUNTIME_GATE
```

---

## 16. Build / Reuse

Phase 1 runtime core использует Python standard library; test dependency — pytest.

Phase 2 canonical validation использует test-only:

- `pytest>=8,<9`;
- `jsonschema>=4.23,<5`.

Перед добавлением OpenCV/geometry solver обязателен отдельный Build / Reuse Check.

---

## 17. Не реализовано после Ring 1

- raw image contour extraction;
- OpenCV primitive detection;
- real `front_clean.png` image fixture;
- IMAGE_PX → MAT_XY_MM transformer для raw anchors;
- general `ConstraintResolver`;
- inferred-constraint promotion policy;
- Dimensioned View renderer;
- persistence/API;
- multi-view geometry;
- CAD-native integration/read-back.

---

## 18. Roadmap position

Основной slice относится к R3 — Semi-Automatic Geometry:

- contours;
- primitives;
- snapping;
- `SketchPackage`;
- downstream DXF/SVG через Chat 4.

Позднее R7 — Multi-View Geometry:

- view relationships;
- advanced alignment;
- cross-view feature matching.

R7 не блокирует FRONT-only R3 baseline.

---

## 19. Change control

Первоначальный Change Request на canonical contracts **закрыт Chat 6** публикацией `mrea.contracts.v1`, policies и canonical fixtures.

Новый Change Request потребуется только для backward-incompatible shared change, например:

- расширение canonical geometry vocabulary;
- изменение SketchPackage fields/semantics;
- shared constraint promotion policy;
- multi-view contract;
- новый calibration/coordinate contract, если текущего v1 недостаточно.

Chat 3 не меняет shared schema напрямую.

---

## 20. Следующий этап после Integrator gate

После подтверждения Ring 1 runtime gate:

1. primitive extraction interface;
2. Build / Reuse Check для OpenCV;
3. real image fixture;
4. contour extraction baseline;
5. line/circle/arc candidate detector;
6. conversion detector output → internal primitives;
7. robustness tests и explicit unresolved behavior;
8. затем constraint-resolution/promotion work.

---

## 21. Текущий статус

Ring 1 geometry/canonical bridge реализован в `main` и передан Chat 6 через `ORCHESTRATOR_HANDOFF.md`.

Shared contracts не изменялись.

Фактическое состояние разработки см. в:

- `docs/IMPLEMENTATION_STATE.md`;
- `docs/IMPLEMENTATION_REPORT_PHASE2_CANONICAL_FRONT_2026-09-29.md`;
- `ORCHESTRATOR_HANDOFF.md`.

При конфликте этого документа с `core/contracts/`, canonical contracts имеют приоритет.
