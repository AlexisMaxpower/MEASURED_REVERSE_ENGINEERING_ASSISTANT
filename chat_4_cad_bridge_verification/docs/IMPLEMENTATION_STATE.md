# Chat 4 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Role:** Chat 4 — CAD Bridge & Verification  
**Canonical baseline:** `mrea.contracts.v1`  
**Orchestrator directive:** `OD-2026-09-29-001`

## Source of truth

1. repository `main`;
2. `core/contracts/`;
3. `tests/fixtures/contracts/`;
4. product SSOT;
5. Chat 4 local docs.

Canonical contract blocker is resolved.

## Implemented

### Canonical intake and internal CAD model

- canonical `SketchPackage v1` → `MappedSketchPackage`;
- mandatory v1 geometry: `POINT`, `LINE`, `CIRCLE`, `ARC`;
- `MAT_XY_MM` → internal mm geometry;
- `Point2D`, `PointEntity`, `LineEntity`, `CircleEntity`, `ArcEntity`, `PolylineEntity`, `CadSketch`;
- finite numeric validation, unique entity IDs, deterministic ordering;
- unsupported canonical entity is rejected instead of silently dropped;
- only `verified=true` dimensions become CAD numerical-transfer truth;
- canonical tolerance: `1e-6 mm` / `1e-6 deg`.

### Generic artifacts

- deterministic SVG;
- DXF R12 via `ezdxf==1.4.4`;
- DXF parse-back test via `ezdxf.read()`;
- canonical `CADPackage v1` builder.

### Verification core

- primary key: `dimension_id`;
- nullable `measurement_id` retained for traceability;
- normalized units: `mm` / `deg`;
- statuses: `VERIFIED`, `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT`;
- absolute non-negative `difference`;
- deterministic item order;
- no silent correction;
- canonical `CADVerificationReport v1` builder;
- `overall_status = VERIFIED` only when all items are `VERIFIED`, otherwise `FAILED`.

### Vendor-neutral adapter/read-back boundary

Implemented:

- `CadAdapter`;
- `CadAdapterError`;
- `CadDimensionBinding`;
- `CadReadBackDimension`;
- `CadReadBack`;
- `CadAdapterResult`.

Traceability chain:

```text
dimension_id
↕
measurement_id
↕
vendor_dimension_ref
↕
normalized read-back value + unit
```

Boundary invariants now enforced:

- adapter result identity must match the adapter identity;
- vendor dimension refs are unique;
- duplicate binding `dimension_id` values are rejected;
- binding for an unknown canonical dimension is rejected;
- binding `measurement_id` must exactly match the canonical traceability value;
- read-back cannot contain an unbound dimension;
- constraint conflicts cannot reference an unbound dimension;
- read-back unit must equal the canonical expected unit before numerical comparison;
- actual values must be finite.

### TEST_DOUBLE and canonical pipeline

`TestDoubleCadAdapter` provides a deterministic no-SOLIDWORKS execution path.

`execute_cad_transfer_v1` runs:

```text
SketchPackage v1
→ MappedSketchPackage
→ CadAdapter.transfer()
→ binding/identity/unit validation
→ normalized CadReadBack
→ VerificationEngine
→ CADPackage v1
→ CADVerificationReport v1
```

Golden TEST_DOUBLE flow matches both canonical fixtures exactly:

- `tests/fixtures/contracts/cad_package_v1.json`;
- `tests/fixtures/contracts/cad_verification_v1.json`.

Negative paths cover `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT`, unknown IDs, unit drift, adapter identity drift and `measurement_id` traceability drift.

## Tests

Repository test inventory after adapter-boundary hardening:

- exporter tests: 3;
- verification tests: 6;
- canonical contract tests: 5;
- adapter/pipeline tests: 9;
- total: **23**.

Verification evidence:

- previous repository baseline: `14 tests — OK`;
- first adapter/pipeline set: `6 tests — OK` in reconstructed local harness;
- hardened reconstructed harness covering exporters + verification + 9 adapter/pipeline tests: `18 tests — OK`.

The 5 schema contract tests were not re-executed in the current container because outbound GitHub DNS is unavailable and a clean checkout cannot be materialized there. Those tests and shared contract files are unchanged by the hardening patch. A fresh full 23-test checkout run remains an integration verification item.

Real SOLIDWORKS API/COM runtime is not yet verified.

## Build / Reuse

- `BUILD_REUSE_CHECK_CAD_CORE.md`;
- `BUILD_REUSE_CHECK_ADAPTER_BOUNDARY.md`.

TEST_DOUBLE is test infrastructure only. No custom CAD kernel or custom COM wrapper is being invented.

## Change requests

- `CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE.md` — resolved;
- `CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` — open.

`CHANGE_REQUEST_002` asks Chat 6 to publish the canonical SOLIDWORKS/.NET/Windows/interop/test-host baseline. No shared contract change is requested.

## Not implemented yet

- artifact persistence/registry integration;
- canonical artifact URI production;
- SOLIDWORKS C#/.NET project;
- SOLIDWORKS COM/API connection;
- native sketch/entity/dimension/constraint creation;
- native persistent mapping for `dimension_id` / `measurement_id`;
- real SOLIDWORKS read-back;
- SOLIDWORKS integration tests;
- Windows/SOLIDWORKS CI/test host.

## External SOLIDWORKS research

Official SOLIDWORKS 2026 documentation confirms that the SOLIDWORKS API is COM-based and supports C#, and that the API SDK provides a Visual C# add-in template. Official installation documentation also lists .NET Framework 4.8.1 as a SOLIDWORKS 2026 prerequisite on supported Windows systems. These facts inform `CHANGE_REQUEST_002`, but do not override Chat 6's authority to choose the repository target environment.

## Next action

1. merge adapter-boundary hardening;
2. wait for / detect an updated Chat 6 directive resolving `CHANGE_REQUEST_002`;
3. once resolved, create the C# SOLIDWORKS adapter project behind the existing normalized boundary;
4. implement canonical POINT/LINE/CIRCLE/ARC creation;
5. implement dimension naming/binding and read-back;
6. verify the same four golden dimensions through real SOLIDWORKS;
7. add constraints and Windows-hosted integration tests.
