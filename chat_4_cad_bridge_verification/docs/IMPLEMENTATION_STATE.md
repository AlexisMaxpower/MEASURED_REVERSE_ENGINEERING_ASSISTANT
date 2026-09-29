# Chat 4 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`  
**Role:** Chat 4 — CAD Bridge & Verification  
**Canonical baseline:** `mrea.contracts.v1`

---

## Source of truth

Актуальный порядок:

1. repository `main`;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT;
5. Chat 4 local docs.

Canonical contract blocker снят Orchestrator-ом.

---

## Implemented

### Internal CAD model

- `Point2D`;
- `PointEntity`;
- `LineEntity`;
- `CircleEntity`;
- `ArcEntity`;
- `PolylineEntity`;
- `CadSketch`;
- finite numeric validation;
- unique entity IDs;
- deterministic entity ordering;
- `MAT_XY_MM` → internal mm geometry baseline.

### Canonical `SketchPackage v1` boundary

Добавлен mapper canonical `SketchPackage` → `MappedSketchPackage`.

Поддерживаемый canonical v1 subset:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Mapper:

- требует `mrea.sketch-package.v1`;
- требует `MAT_XY_MM`;
- сохраняет canonical entity/dimension/constraint/unresolved data;
- не молча отбрасывает unsupported entity;
- выделяет только `verified=true` dimensions как CAD numerical-transfer truth;
- использует `dimension_id` как primary CAD verification key;
- сохраняет nullable `measurement_id` как traceability link;
- применяет canonical transfer tolerance: `1e-6 mm` / `1e-6 deg`.

### Generic CAD artifacts

- deterministic SVG;
- DXF R12 через `ezdxf==1.4.4`;
- DXF parse-back test через `ezdxf.read()`.

### `CADPackage v1`

Добавлен builder canonical `mrea.cad-package.v1`.

Artifact storage/URI generation остаётся отдельной boundary: builder принимает уже сформированные `ArtifactReference` values и не выдумывает storage URI.

### Verification core

Internal model переработан под canonical contract:

- key — `dimension_id`, не `measurement_id`;
- `measurement_id` nullable и сохраняется отдельно;
- units: `mm` / `deg`;
- `difference` — absolute non-negative difference;
- input order сохраняется для deterministic canonical output;
- duplicate `dimension_id` rejected;
- `VERIFIED`, `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT`;
- no silent correction.

### `CADVerificationReport v1`

Добавлен mapper internal report → canonical `mrea.cad-verification.v1`.

Canonical policy output:

```text
kind = NUMERICAL_TRANSFER
length tolerance = 1e-6 mm
angle tolerance = 1e-6 deg
```

`overall_status`: все items VERIFIED → `VERIFIED`, иначе → `FAILED`.

---

## Tests

Current suite:

- exporter tests: 3;
- verification tests: 6;
- canonical contract tests: 5;
- total: **14**.

Contract tests читают canonical schema/fixtures из repository root и проверяют exact golden outputs.

### Local verification

```text
Ran 14 tests
OK
```

Проверено на Python 3.13 с `ezdxf 1.4.4` и `jsonschema 4.26.0`.

Не проверено: real SOLIDWORKS import/API/COM runtime.

---

## Resolved blocker

`CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE.md` закрыт: Orchestrator опубликовал canonical schemas, fixtures и policies.

---

## Not implemented yet

- Artifact persistence/registry integration;
- canonical artifact URI production;
- dimension/constraint application в vendor CAD;
- SOLIDWORKS C#/.NET project;
- SOLIDWORKS COM/API connection;
- SolidWorks entity/constraint/dimension creation;
- persistent CAD mapping for `dimension_id` / `measurement_id`;
- CAD read-back adapter;
- SolidWorks integration tests;
- Windows/SOLIDWORKS CI/test host.

---

## Remaining external dependency

SOLIDWORKS stage требует target environment decision:

- supported SOLIDWORKS version;
- .NET target;
- interop strategy;
- Windows test host;
- availability of real SOLIDWORKS runtime for integration tests.

До этого generic contract/DXF/SVG/verification slice остаётся тестируемым без SOLIDWORKS.

---

## Next action

1. определить vendor-neutral CAD read-back interface;
2. зафиксировать mapping `dimension_id` ↔ vendor dimension handle/name;
3. подготовить SOLIDWORKS adapter project skeleton после environment decision;
4. создать TEST_DOUBLE adapter для полного canonical golden flow без installed SOLIDWORKS;
5. затем заменить TEST_DOUBLE реальным SOLIDWORKS API adapter.
