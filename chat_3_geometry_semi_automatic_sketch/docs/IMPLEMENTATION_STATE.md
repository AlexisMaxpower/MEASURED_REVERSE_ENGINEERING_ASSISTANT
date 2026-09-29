# Chat 3 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Active directive:** `OD-2026-09-29-001`

## Текущее состояние

Chat 6 / Integrator опубликовал canonical v1 contracts, policies и fixtures и добавил `ORCHESTRATOR_DIRECTIVE.md` непосредственно в Chat 3 workspace.

Главный прежний blocker снят. Chat 3 теперь потребляет Integrator-owned contracts и реализует canonical FRONT pipeline до `SketchPackage v1`, не изменяя shared schemas самостоятельно.

## Canonical inputs / output

Inputs:

- `/core/contracts/mrea_contracts_v1.schema.json`;
- `/core/contracts/POLICIES_V1.md`;
- `/tests/fixtures/contracts/capture_package_v1.json`;
- `/tests/fixtures/contracts/measurement_package_v1.json`.

Golden output:

- `/tests/fixtures/contracts/sketch_package_v1.json`.

Coordinate system для текущего acceptance target:

```text
MAT_XY_MM
```

## Реализовано

### Internal geometry core

- `Point2D`;
- `PointEntity`;
- `Line`;
- `Circle`;
- `Arc`;
- `GeometryGraph`;
- deterministic endpoint/point adjacency;
- `AnchorRef`;
- `MeasurementRef`;
- `AnchorEntityMatcher`;
- feature-aware matching через canonical `feature_id`;
- coordinate-distance fallback;
- `DimensionBinder`;
- geometry estimates для supported linear/diameter/radius/center-distance cases;
- `ConstraintCandidateEngine`;
- internal candidates: `HORIZONTAL`, `VERTICAL`, `PARALLEL`, `PERPENDICULAR`, `EQUAL`, `CONCENTRIC`;
- `GeometryConflictDetector`;
- explicit `UnresolvedBinding`;
- deterministic internal `GeometryDraft`.

### Canonical bridge

- `CanonicalInputAdapter`;
- CapturePackage/MeasurementPackage identity consistency checks;
- v1 FRONT selection;
- `MAT_XY_MM` enforcement;
- canonical anchor → internal anchor conversion;
- `measurement_id` preservation;
- `SketchPackageBuilder`;
- canonical POINT/LINE/CIRCLE/ARC serialization;
- canonical dimension type mapping;
- deterministic entity ordering;
- deterministic dimension ordering;
- canonical unresolved projection;
- verified-vs-derived conflicts preserved as unresolved instead of silent correction;
- inferred constraints intentionally kept internal for current golden baseline.

### Fixtures / tests

- Phase 1 internal FRONT fixture;
- canonical FRONT primitive-detector-output fixture;
- Phase 1 unit tests;
- Phase 2 canonical golden/schema tests;
- JSON Schema Draft 2020-12 validation through test-only `jsonschema` dependency.

## Главный метрологический инвариант

```text
verified physical measurement > image-derived / geometry-derived estimate
```

Verified value никогда не переписывается геометрией. Расхождение сохраняется явно.

## Canonical FRONT acceptance path

```text
CapturePackage v1
        +
MeasurementPackage v1
        ↓
CanonicalInputAdapter
        ↓
normalized measurements + feature hints
        +
primitive detector output fixture
        ↓
GeometryGraph
        ↓
feature-aware measurement binding
        ↓
geometry estimate
        ↓
conflict / unresolved detection
        +
internal constraint candidates
        ↓
SketchPackageBuilder
        ↓
SketchPackage v1
        ↓
JSON Schema validation
        ↓
exact golden comparison
```

## Проверка

### Phase 1 historical verification

Ранее зафиксирован exact-payload runtime run:

```text
6 passed in 0.06s
```

### Phase 2

Добавлены acceptance tests для:

- exact equality с Integrator `sketch_package_v1.json`;
- canonical JSON Schema validation;
- deterministic result при reverse primitive order;
- сохранения `M-WIDTH`, `M-HEIGHT`, `M-HOLE`, `M-CENTER`;
- обязательного v1 `POINT`.

Runtime `pytest` Phase 2 в текущей ChatGPT sandbox не выполнен: среда не разрешает DNS-доступ к `github.com`, а repository CI workflow отсутствует. Поэтому Phase 2 не помечается ложным `passed`; состояние — **runtime verification pending**.

## Не реализовано

- raw image contour extraction;
- OpenCV primitive detection;
- реальный `fixture://images/front_clean.png` artifact отсутствует в repository;
- IMAGE_PX → MAT_XY_MM transformer для non-canonical/raw anchors;
- general `ConstraintResolver`;
- policy продвижения inferred constraints в canonical `constraints`;
- Dimensioned View renderer;
- persistence/API;
- multi-view geometry;
- CAD integration/read-back.

## Shared ownership

Chat 3 не изменяет самостоятельно:

- `/core/contracts/`;
- `/core/domain/shared/`;
- `/tests/fixtures/contracts/`;
- contracts/policies Integrator;
- директории других chats.

## Текущие ограничения canonical FRONT baseline

1. Primitive geometry поступает из локального deterministic fixture, моделирующего результат будущего detector-а.
2. Canonical golden anchors уже находятся в `MAT_XY_MM`, поэтому pixel transform в этом acceptance case не нужен.
3. `feature_id` используется как primary semantic association hint; coordinate matching остаётся fallback.
4. Pure inferred constraints пока не экспортируются, поскольку canonical golden fixture содержит пустой `constraints`.
5. Linear measurement association и CAD-oriented dimension host различаются: measured left/right edges могут породить canonical width dimension на bottom line.

## Следующий шаг

1. Integrator должен выполнить/review Phase 2 runtime acceptance или предоставить CI/release-gate environment.
2. После зелёного canonical FRONT gate — реализовать primitive extraction boundary.
3. Выполнить Build / Reuse spike для OpenCV contour/line/circle/arc detection на реальном image fixture.
4. Не расширять v1 geometry vocabulary без Change Request.

Подробности:

- `BUILD_REUSE_CHECK_PHASE2_CANONICAL_BRIDGE.md`;
- `IMPLEMENTATION_REPORT_PHASE2_CANONICAL_FRONT_2026-09-29.md`.
