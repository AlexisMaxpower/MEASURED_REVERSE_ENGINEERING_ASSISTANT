# Build / Reuse Check — Phase 2 Canonical Bridge

**Дата:** 2026-09-29  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Directive:** `OD-2026-09-29-001`

## Problem

Chat 3 должен потреблять Integrator-owned `CapturePackage v1` и `MeasurementPackage v1`, формировать `SketchPackage v1`, сохранять `measurement_id`, соблюдать `MAT_XY_MM`, публиковать ambiguous/conflicting geometry через `unresolved` и проходить canonical JSON Schema/golden verification.

## Existing solution / reuse

### Shared contracts

Используются без копирования и переопределения:

- `/core/contracts/mrea_contracts_v1.schema.json`;
- `/core/contracts/POLICIES_V1.md`;
- `/tests/fixtures/contracts/capture_package_v1.json`;
- `/tests/fixtures/contracts/measurement_package_v1.json`;
- `/tests/fixtures/contracts/sketch_package_v1.json`.

### JSON Schema validation

Reuse: `jsonschema >=4.23,<5` только как test dependency.

Используется для Draft 2020-12 validation `SketchPackage` через `$defs/SketchPackage` canonical schema.

## Can use existing solution?

**YES** для schema validation и shared contract definitions.  
**PARTIAL** для geometry semantics: generic JSON Schema не реализует feature binding, geometry graph, conflict policy или deterministic CAD-oriented dimension association.

## What MREA reuses

- canonical schemas/fixtures от Integrator;
- `jsonschema` validator;
- существующий Chat 3 Phase 1 geometry core.

## What Chat 3 builds

- `CanonicalInputAdapter`;
- feature-aware anchor→entity association;
- mandatory `POINT` support;
- `SketchPackageBuilder`;
- deterministic entity/dimension ordering;
- canonical unresolved/conflict projection;
- exact FRONT golden test.

## Why custom code is required

Canonical schema описывает wire format, но не алгоритм преобразования measurement anchors и geometry candidates в CAD-oriented entities/dimensions. Эти правила относятся к ownership Chat 3.

## Lock-in risk

Низкий. `jsonschema` используется только в tests; runtime domain не зависит от конкретного validator implementation. Shared contract dependency намеренная и является архитектурной границей системы.

## Fallback

При замене validator library сохраняются те же Integrator-owned JSON Schema и fixtures. При изменении shared contract Chat 3 обязан получить новую directive/Change Request и адаптировать bridge, а не менять schema локально.
