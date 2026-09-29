# Chat 4 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main` after integration  
**Role:** Chat 4 — CAD Bridge & Verification  
**Canonical baseline:** `mrea.contracts.v1`  
**Orchestrator directive:** `OD-2026-09-29-001`

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

Canonical `SketchPackage` maps to `MappedSketchPackage`.

Supported mandatory v1 subset:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Mapper:

- requires `mrea.sketch-package.v1`;
- requires `MAT_XY_MM`;
- preserves canonical entity/dimension/constraint/unresolved data;
- rejects unsupported entity instead of silently dropping it;
- uses only `verified=true` dimensions as CAD numerical-transfer truth;
- uses `dimension_id` as primary CAD verification key;
- preserves nullable `measurement_id` as traceability link;
- applies canonical transfer tolerance `1e-6 mm` / `1e-6 deg`.

### Generic CAD artifacts

- deterministic SVG;
- DXF R12 via `ezdxf==1.4.4`;
- DXF parse-back test via `ezdxf.read()`.

### `CADPackage v1`

Canonical `mrea.cad-package.v1` builder implemented.

Artifact storage/URI generation remains a separate boundary: the builder accepts already formed `ArtifactReference` values and does not invent storage URIs.

### Verification core

- key: `dimension_id`;
- nullable `measurement_id` retained separately;
- units: `mm` / `deg`;
- `difference` is absolute non-negative difference;
- input order preserved for deterministic canonical output;
- duplicate `dimension_id` rejected;
- statuses: `VERIFIED`, `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT`;
- no silent correction.

### `CADVerificationReport v1`

Internal report maps to canonical `mrea.cad-verification.v1`.

Canonical policy:

```text
kind = NUMERICAL_TRANSFER
length tolerance = 1e-6 mm
angle tolerance = 1e-6 deg
```

`overall_status`: all items VERIFIED → `VERIFIED`; otherwise → `FAILED`.

### Vendor-neutral CAD adapter/read-back boundary

Implemented:

- `CadAdapter` protocol;
- `CadDimensionBinding`;
- `CadReadBackDimension`;
- `CadReadBack`;
- `CadAdapterResult`;
- `CadAdapterError`.

The boundary explicitly preserves:

```text
dimension_id
↕
measurement_id (nullable traceability)
↕
vendor_dimension_ref
↕
normalized read-back value + unit
```

Rules:

- vendor dimension refs are unique inside one adapter result;
- read-back cannot contain an unbound `dimension_id`;
- constraint conflicts cannot reference an unbound dimension;
- actual values must be finite;
- vendor read-back is normalized to canonical `mm` / `deg`;
- unit mismatch is rejected before numerical verification.

### TEST_DOUBLE adapter

Implemented deterministic `TestDoubleCadAdapter` for full flow without installed SOLIDWORKS.

Default behavior:

- creates deterministic vendor references `TEST_DOUBLE::DIM::<dimension_id>`;
- echoes verified canonical dimension values as normalized CAD read-back;
- emits no fake artifacts;
- preserves `measurement_id` mapping.

Controlled negative modes:

- actual value override → `MISMATCH` test;
- omitted read-back → `MISSING` test;
- explicit constraint conflict → `CONSTRAINT_CONFLICT` test;
- unknown dimension controls rejected.

### Canonical CAD transfer pipeline

Implemented `execute_cad_transfer_v1`:

```text
canonical SketchPackage
→ MappedSketchPackage
→ CadAdapter.transfer()
→ normalized CadReadBack
→ unit validation
→ VerificationEngine
→ canonical CADPackage
→ canonical CADVerificationReport
```

With `TestDoubleCadAdapter`, golden fixture produces both canonical outputs exactly:

- `tests/fixtures/contracts/cad_package_v1.json`;
- `tests/fixtures/contracts/cad_verification_v1.json`.

---

## Tests

Repository test inventory after this iteration:

- exporter tests: 3;
- verification tests: 6;
- canonical contract tests: 5;
- adapter/pipeline tests: 6;
- total: **20**.

New adapter/pipeline tests cover:

1. exact golden `CADPackage` + `CADVerificationReport` flow;
2. deterministic `dimension_id` / `measurement_id` / vendor ref mapping;
3. `MISMATCH` without silent correction;
4. `MISSING`;
5. `CONSTRAINT_CONFLICT`;
6. unknown test controls rejection;
7. unit mismatch rejection before numerical comparison.

### Verification evidence

Previous baseline verification recorded in repository:

```text
Ran 14 tests
OK
```

The new adapter/pipeline implementation was independently executed against the canonical golden values in a local reconstructed harness:

```text
Ran 6 adapter/pipeline tests
OK
```

A fresh full 20-test checkout run could not be executed in the current tool container because outbound GitHub DNS access is unavailable there. Source changes are therefore marked ready for repository integration review, while a clean-checkout full-suite run remains an integration verification item.

Not verified: real SOLIDWORKS import/API/COM runtime.

---

## Build / Reuse

- `BUILD_REUSE_CHECK_CAD_CORE.md` — generic model/export/verification decisions;
- `BUILD_REUSE_CHECK_ADAPTER_BOUNDARY.md` — vendor-neutral adapter/read-back and TEST_DOUBLE decision.

No CAD kernel or mocking framework is introduced for the adapter boundary. TEST_DOUBLE is test infrastructure only, not a production CAD implementation.

---

## Resolved blockers

`CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE.md` is closed: Orchestrator published canonical schemas, fixtures and policies.

The previous generic read-back/test-double blocker is also resolved by this iteration.

---

## Not implemented yet

- Artifact persistence/registry integration;
- canonical artifact URI production;
- actual dimension/constraint application in vendor CAD;
- SOLIDWORKS C#/.NET project;
- SOLIDWORKS COM/API connection;
- SOLIDWORKS entity/constraint/dimension creation;
- persistent SOLIDWORKS mapping for `dimension_id` / `measurement_id`;
- real SOLIDWORKS CAD read-back;
- SOLIDWORKS integration tests;
- Windows/SOLIDWORKS CI/test host.

---

## Remaining external dependency

SOLIDWORKS stage requires an integration environment decision:

- supported SOLIDWORKS version;
- .NET target;
- SOLIDWORKS interop strategy;
- Windows test host;
- availability of real SOLIDWORKS runtime for integration tests.

The vendor-neutral contract boundary is intentionally complete enough that these decisions no longer block generic CAD verification development.

---

## Next action

1. publish this adapter/read-back baseline to `main`;
2. notify Chat 6 through repository-visible state that pure generic CAD gate is complete;
3. define the SOLIDWORKS adapter project/environment baseline with Chat 6;
4. create C# adapter skeleton behind the existing normalized boundary;
5. implement entity creation for canonical POINT/LINE/CIRCLE/ARC subset;
6. implement dimension binding/read-back and compare against the same canonical golden fixture;
7. only then add constraints and Windows/SOLIDWORKS integration tests.
