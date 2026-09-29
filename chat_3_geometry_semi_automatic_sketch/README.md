# Chat 3 — Geometry & Semi-Automatic Sketch

Эта директория является изолированной рабочей областью Chat 3 проекта MREA.

## Ownership

Chat 3 отвечает за vertical slice `Geometry & Semi-Automatic Sketch`: geometry domain model, contour/primitive extraction boundary, `POINT`/`LINE`/`CIRCLE`/`ARC`, `GeometryGraph`, constraint candidates/resolution внутри slice, binding verified measurements, geometry conflict detection, dimensioned view и deterministic `SketchPackage`.

Главный инвариант:

```text
verified physical measurement > image-derived / geometry-derived estimate
```

Chat 3 не владеет shared contracts и не изменяет их без решения Chat 6 / Integrator.

## Canonical boundary

```text
CapturePackage v1 + MeasurementPackage v1
                    ↓
        CanonicalInputAdapter
                    ↓
          Geometry pipeline
                    ↓
         SketchPackage v1
```

Canonical contracts и fixtures опубликованы Chat 6 и находятся в:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/capture_package_v1.json`;
- `tests/fixtures/contracts/measurement_package_v1.json`;
- `tests/fixtures/contracts/sketch_package_v1.json`.

Текущий canonical geometry coordinate system: `MAT_XY_MM`.

## Ring 1 — текущее состояние

После directive `OD-2026-09-29-001` реализованы:

- internal geometry core;
- `PointEntity`, `Line`, `Circle`, `Arc`;
- deterministic `GeometryGraph`;
- feature-aware anchor → entity binding;
- `DimensionBinder`;
- verified-vs-derived conflict detection;
- explicit unresolved bindings;
- constraint candidates;
- canonical `CapturePackage` / `MeasurementPackage` adapter;
- deterministic `SketchPackageBuilder`;
- canonical FRONT golden fixture path;
- JSON Schema/golden/determinism/measurement-link tests.

Shared contracts Chat 3 не изменял.

## Verification status

Phase 1 historical runtime verification:

```text
6 passed in 0.06s
```

Phase 2 acceptance tests находятся в repository, но runtime gate должен выполнить Integrator/окружение с repository checkout и test dependencies. Текущий handoff status:

```text
READY_FOR_INTEGRATOR_RUNTIME_GATE
```

## Основные файлы

- `ORCHESTRATOR_DIRECTIVE.md` — действующая директива Chat 6;
- `ORCHESTRATOR_HANDOFF.md` — результат Ring 1 для Chat 6;
- `docs/CHAT_3_ROLE.md` — границы роли и архитектурные правила;
- `docs/IMPLEMENTATION_STATE.md` — актуальное фактическое состояние;
- `docs/IMPLEMENTATION_REPORT_PHASE2_CANONICAL_FRONT_2026-09-29.md` — подробный отчёт canonical FRONT slice;
- `src/mrea_geometry/` — runtime geometry core и canonical bridge;
- `tests/` — internal и canonical acceptance tests.

## Следующий этап после Integrator gate

- primitive extraction boundary;
- отдельный Build / Reuse Check для OpenCV;
- contour/line/circle/arc detector baseline на реальном image fixture;
- дальнейшая constraint-resolution policy;
- IMAGE_PX → MAT_XY_MM path при появлении такого upstream input.

Не расширять canonical v1 geometry vocabulary без Change Request к Chat 6.
