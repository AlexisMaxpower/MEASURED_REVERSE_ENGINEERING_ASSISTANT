# Chat 4 — Implementation State

**Дата:** 2026-09-29  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Role:** Chat 4 — CAD Bridge & Verification  
**Canonical baseline:** `mrea.contracts.v1`  
**Orchestrator directive:** `OD-2026-09-29-002`  
**Pass 2 branch:** `chat-4/pass-2`

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
- SOLIDWORKS-agent boundary tests: 9;
- total: **32**.

Verification evidence:

- previous repository baseline: `14 tests — OK`;
- first adapter/pipeline set: `6 tests — OK` in reconstructed local harness;
- hardened reconstructed harness covering exporters + verification + 9 adapter/pipeline tests: `18 tests — OK`;
- Pass 2 harness covering exporters + verification + existing adapter/pipeline + 9 SOLIDWORKS-agent tests: `27 tests — OK`.

The 5 schema contract tests were not re-executed in the current container because outbound GitHub DNS is unavailable and a clean checkout cannot be materialized there. Those tests and shared contract files are unchanged by the hardening patch. A fresh full 32-test checkout run remains an Integrator verification item.

Real SOLIDWORKS API/COM runtime is not yet verified.

## Pass 2 — SOLIDWORKS 2026 CAD Agent

ADR-001 resolves the vendor environment baseline:

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- C# / .NET Framework 4.8;
- x64 out-of-process user-session agent;
- `[STAThread]` COM context;
- local official SOLIDWORKS interop references;
- no proprietary binaries committed.

Implemented slice-local production path:

- `SolidWorksAgentConfig`;
- `SubprocessSolidWorksAgentRunner`;
- `SolidWorksAgentAdapter`;
- protocol `mrea.solidworks-agent.v1`;
- preflight for unresolved verified geometry/measurements;
- explicit rejection of unsupported constraints/entities/units/dimension types;
- C# agent project under `solidworks_agent/`;
- attach/launch SOLIDWORKS;
- create a part and FRONT sketch;
- LINE/CIRCLE creation in SOLIDWORKS system units;
- DISTANCE/DIAMETER/RADIUS dimension creation path;
- `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` bindings;
- read-back to canonical mm;
- `.SLDPRT` save + SHA-256 ArtifactReference-compatible data;
- build and real-host golden scripts.

### Real-host status

**UNVERIFIED.** The current execution environment is Linux and has neither MSBuild/.NET Framework tooling nor SOLIDWORKS 2026 COM/interop runtime. C# files therefore have not been represented as compiled or COM-tested. Python AST, csproj XML, and pure adapter boundary behavior were checked.

## Build / Reuse

- `BUILD_REUSE_CHECK_CAD_CORE.md`;
- `BUILD_REUSE_CHECK_ADAPTER_BOUNDARY.md`;
- `BUILD_REUSE_CHECK_SOLIDWORKS_AGENT.md`.

Official SOLIDWORKS API/interop is reused; no CAD kernel, COM replacement, proprietary DLL copy, or second artifact-storage system is introduced.

## Change requests

- `CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE.md` — resolved;
- `CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` — resolved by ADR-001;
- no new shared-contract Change Request in Pass 2.

## Remaining after Pass 2

- real Windows 11 + SOLIDWORKS 2026 build/smoke/golden execution;
- POINT/ARC mapping in real vendor worker;
- ANGLE dimension mapping;
- canonical constraint → SOLIDWORKS relation mapping and conflict extraction;
- broader vendor capability reporting;
- Windows-hosted automated integration gate.

## Next acceptance action

Chat 6 should review branch `chat-4/pass-2`, rerun ordinary tests from a complete checkout, and classify the vendor runtime as `UNVERIFIED` until `scripts/run_solidworks_golden.ps1` returns `REAL_HOST_RESULT=VERIFIED` on the supported host.
