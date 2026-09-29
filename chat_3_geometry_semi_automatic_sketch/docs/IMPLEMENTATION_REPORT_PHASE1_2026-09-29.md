# IMPLEMENTATION_REPORT — Chat 3 Phase 1 Geometry Core

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch

## 1. Что реализовано

- internal geometry models: `Point2D`, `Line`, `Circle`, `Arc`;
- normalized `AnchorRef` и contract-neutral `MeasurementRef`;
- deterministic `GeometryGraph` по endpoint incidence;
- `AnchorEntityMatcher`;
- `ConstraintCandidateEngine` для `HORIZONTAL`, `VERTICAL`, `PARALLEL`, `PERPENDICULAR`, `EQUAL`, `CONCENTRIC` candidates;
- `DimensionBinder`;
- geometry estimates для поддерживаемых measurement types;
- `GeometryConflictDetector`;
- explicit `UnresolvedBinding`;
- deterministic `GeometryDraft` internal output;
- FRONT internal fixture;
- unit/golden-style deterministic tests.

Ключевое правило соблюдается: verified measurement value сохраняется неизменным, а несовпадение с geometry estimate превращается в explicit conflict.

## 2. Какие исходные contracts использованы

Canonical shared contracts не использовались, потому что Integrator schemas/fixtures ещё отсутствуют.

Использованы SSOT semantics и фактический upstream Chat 2 implementation для проверки реальной формы anchors. Chat 2 хранит Phase A anchors как pixel points; Chat 3 не импортирует Chat 2 module и не объявляет его internal model shared contract.

Internal `AnchorRef` предполагает, что upstream adapter уже перевёл anchor в coordinate system geometry. Конкретный canonical pixel→MAT_XY_MM transform пока не фиксируется.

## 3. Какие файлы изменены/добавлены

- `src/mrea_geometry/__init__.py`;
- `src/mrea_geometry/models.py`;
- `src/mrea_geometry/graph.py`;
- `src/mrea_geometry/core.py`;
- `tests/fixtures/internal/front_plate_case.json`;
- `tests/test_geometry_core.py`;
- `pyproject.toml`;
- `docs/BUILD_REUSE_CHECK_PHASE1.md`;
- этот report.

## 4. Какие зависимости добавлены

Runtime dependencies: none.

Test-only dependency: `pytest>=8,<9`.

Python baseline: `>=3.11`.

## 5. Какие тесты добавлены

Проверяются: line/circle/arc representation, GeometryGraph adjacency, deterministic output, сохранение verified value и `measurement_id`, constraint candidates, explicit conflict и explicit unresolved binding.

## 6. Какие тесты прошли

На локальном exact-payload воспроизведении файлов перед записью в repository:

```text
6 passed in 0.06s
```

GitHub Actions/CI в этой итерации не запускался.

## 7. Что не проверено

- canonical contract validation;
- реальный `CapturePackage` / `MeasurementPackage` adapter;
- pixel→MAT_XY_MM calibration transform;
- OpenCV contour/primitive extraction;
- real image fixtures;
- constraint solving;
- canonical `SketchPackage` serialization;
- downstream CAD consumption;
- Dimensioned View rendering.

## 8. Известные ограничения

- primitives приходят уже созданными;
- anchor matching работает только в общей normalized coordinate system;
- `max_distance=0.75` — internal baseline, не canonical tolerance policy;
- geometry estimates покрывают subset measurement types;
- constraint engine генерирует candidates, но не выполняет general solving;
- `GeometryDraft` — internal format, не `SketchPackage v1`.

## 9. Новые технические знания

Фактический upstream Chat 2 Phase A хранит anchors как `FeatureAnchor(view_id, reference_frame_id, x_px, y_px)`. Между Chat 2 internal state и Chat 3 normalized geometry нужен явный coordinate-transform/adapter boundary:

```text
raw/pixel anchor
→ coordinate transform
→ normalized AnchorRef
→ primitive association
→ measurement binding
```

## 10. Change Requests

Integrator должен определить canonical `MeasurementPackage v1`, anchor/feature representation, coordinate transform metadata, `SketchPackage v1`, tolerance policy, unresolved/conflict representation и canonical fixtures.

## 11. Что готово к интеграции

Готово как isolated internal core: geometry primitives, topology graph, normalized-anchor association, measurement binding, conflict/unresolved logic, deterministic constraint candidates и deterministic internal draft.

Не готово как cross-slice integration: canonical upstream adapter, canonical `SketchPackage` output, contract tests и CAD integration.
