# Chat 3 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch

---

## Current repository state

При подключении Chat 3 в `main` уже существовала область Chat 1:

```text
chat_1_project_guided_capture/
```

На момент проверки product code, canonical shared contracts и contract fixtures в repository отсутствовали.

Создана изолированная область Chat 3:

```text
chat_3_geometry_semi_automatic_sketch/
├─ README.md
└─ docs/
   ├─ CHAT_3_ROLE.md
   └─ IMPLEMENTATION_STATE.md
```

Никакие файлы Chat 1, shared contracts, global architecture или ownership других слайсов не изменялись.

---

## Implemented

- repository access verified;
- фактическая структура `main` проверена перед изменениями;
- recent commits и open PR state проверены;
- Chat 3 ownership изолирован в собственной директории;
- role boundaries documented;
- upstream/downstream contracts documented на уровне SSOT names;
- метрологический приоритет `verified measurement > image-derived estimate` зафиксирован;
- Geometry pipeline documented;
- primitive/constraint baseline documented;
- deterministic-output requirements documented;
- FRONT golden-case scope documented;
- initial Change Request для отсутствующих canonical v1 contracts/fixtures подготовлен;
- implementation sequence зафиксирован.

---

## Not implemented yet

- geometry domain code;
- `GeometryFeatureExtractor`;
- contour extraction implementation;
- `PrimitiveDetector`;
- line/circle/arc runtime support;
- `GeometryGraph`;
- `ConstraintCandidateEngine`;
- `ConstraintResolver`;
- `DimensionBinder`;
- `GeometryConflictDetector`;
- `DimensionedViewRenderer`;
- `SketchPackageBuilder`;
- persistence/API, если они потребуются реальной repository architecture;
- unit tests;
- contract tests;
- golden tests;
- runtime dependency selection.

---

## Contracts status

Chat 3 требует следующие shared contracts из SSOT:

- `CapturePackage` — canonical schema не присутствует в repository;
- `PhysicalMeasurement` — canonical schema не присутствует в repository;
- `MeasurementPackage` — canonical schema не присутствует в repository;
- `SketchPackage` — canonical schema не присутствует в repository;
- `ArtifactReference` — canonical schema не присутствует в repository.

Canonical fixtures under `/tests/fixtures/contracts/` также отсутствуют на момент проверки.

Chat 3 не будет определять эти shared contracts односторонне.

---

## Current blocker

Внутренний geometry core можно проектировать без фиксации shared schema, однако integration-ready implementation и contract/golden verification нельзя честно объявить завершёнными, пока Integrator не опубликует canonical v1 contracts и fixtures.

Особенно критичны:

- representation upstream view/image references;
- `PhysicalMeasurement` anchors;
- verified/provenance semantics;
- stable ID policy;
- canonical `SketchPackage` entities/constraints/dimensions/unresolved representation.

---

## Planned implementation sequence

### Phase 1 — Contract intake

- повторно проверить repository tree;
- получить canonical fixtures;
- проверить Measurement anchors/provenance;
- проверить SketchPackage schema;
- не менять contracts локально.

### Phase 2 — Geometry domain baseline

- internal entity/feature model;
- stable internal IDs;
- provenance state;
- normalized coordinate handling;
- deterministic serialization rules.

### Phase 3 — Primitive baseline

- contour input;
- line detection;
- circle detection;
- arc detection;
- deterministic primitive normalization;
- ambiguous candidates остаются unresolved/candidate.

### Phase 4 — GeometryGraph

- topology;
- entity relationships;
- feature relationships;
- measurement anchor binding points;
- candidate constraints.

### Phase 5 — Measurement binding & conflicts

- bind verified measurements by `measurement_id`;
- preserve source/provenance;
- detect image-vs-measurement conflict;
- detect missing/ambiguous anchors;
- never silently modify verified value.

### Phase 6 — Constraint baseline

- deterministic relation candidates;
- minimal resolver;
- verified dimensions as hard truth;
- explicit `CONSTRAINT_CONFLICT` path.

### Phase 7 — SketchPackage

- canonical entity output;
- constraints;
- dimensions;
- unresolved/conflicts;
- stable ordering/IDs;
- source-view links.

### Phase 8 — Verification

- simple FRONT golden fixture;
- exact expected SketchPackage;
- repeated-run determinism test;
- measured vs inferred assertions;
- contract validation.

### Phase 9 — Dimensioned View

- clean reference base;
- geometry overlay;
- dimensions;
- confidence/provenance representation;
- output remains derived artifact, not measurement truth.

---

## Build / Reuse status

No runtime dependency has been selected yet.

SSOT baseline permits OpenCV and existing geometry libraries/solver components. Before adding any nontrivial dependency, Chat 3 must record a Build / Reuse Check covering:

- exact problem;
- available open-source option;
- fitness for use;
- what MREA reuses;
- what remains custom;
- lock-in risk;
- fallback.

---

## Verification performed

Verified:

- target GitHub repository exists;
- connector has push/admin access;
- default branch is `main`;
- pre-change repository tree contained Chat 1 area only;
- recent repository commits were Chat 1 initialization/documentation;
- no open pull requests were present during pre-change check;
- Chat 3 README commit succeeded;
- Chat 3 role-document commit succeeded;
- this implementation-state file was created in Chat 3 docs area.

Not verified yet:

- runtime architecture;
- Python package layout;
- geometry library compatibility;
- OpenCV behavior on real fixtures;
- constraint solver suitability;
- numerical tolerances;
- canonical schema validation;
- application tests;
- end-to-end CAD compatibility.

---

## Integration readiness

Ready for Integrator review:

- Chat 3 ownership directory;
- role documentation;
- explicit contract dependencies;
- initial Change Request;
- phased implementation plan.

Not ready for product integration:

- all runtime Geometry/Sketch functionality;
- `SketchPackage` generation;
- golden/contract tests.

---

## Next action

После появления Integrator contracts/fixtures Chat 3 должен повторно проверить текущий repository state и начать не с advanced CV, а с deterministic FRONT fixture pipeline:

```text
fixture
→ primitives
→ GeometryGraph
→ measurement binding
→ conflict detection
→ minimal constraints
→ SketchPackage
→ golden test
```
