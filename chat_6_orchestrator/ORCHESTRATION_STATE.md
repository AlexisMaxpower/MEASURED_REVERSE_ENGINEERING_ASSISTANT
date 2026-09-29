# MREA Orchestration State

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive revision:** `OD-2026-09-29-001`  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** R0 Contracts & Fixtures published

## Source-of-truth hierarchy
1. Current repository state on `main`.
2. Canonical shared contracts in `core/contracts/`.
3. Canonical fixtures in `tests/fixtures/contracts/`.
4. Product SSOT v0.1 plus orchestration addendum.
5. Slice-local documentation.

If slice-local documentation conflicts with canonical contracts, `core/contracts/` wins.

## Current integration status
- Chat 1: implementation in progress; adapt outward boundary to canonical `ProjectContract` and `CapturePackage`.
- Chat 2: Phase A implementation in progress; internal model remains allowed; shared serialization targets canonical `PhysicalMeasurement` / `MeasurementPackage`.
- Chat 3: canonical-contract blocker removed for deterministic FRONT geometry pipeline.
- Chat 4: canonical-contract blocker removed for verification core and generic DXF/SVG boundary; SOLIDWORKS runtime remains environment-dependent.
- Chat 5: implementation in progress; lifecycle shared output adapts to canonical `LifecycleEvent`.

## Shared rules
- IDs are opaque non-empty strings. UUIDs are recommended but not required by the wire contract.
- Timestamps are UTC/RFC3339.
- v1 length unit is `mm`; angle unit is `deg`.
- Verified physical measurements are never silently modified by CV/AI.
- CAD transfer verification is numerical transfer verification, not manufacturing tolerance verification.
- Default CAD transfer tolerance: `1e-6 mm` for length and `1e-6 deg` for angle.
- SketchPackage v1 mandatory geometry subset: POINT, LINE, CIRCLE, ARC.
- Unsupported/ambiguous geometry is explicit in `unresolved`.

## Published canonical fixtures
- `tests/fixtures/contracts/project_v1.json`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`
- `tests/fixtures/contracts/sketch_package_v1.json`
- `tests/fixtures/contracts/cad_package_v1.json`
- `tests/fixtures/contracts/cad_verification_v1.json`
- `tests/fixtures/contracts/lifecycle_event_v1.json`

## Change control
Any backward-incompatible shared contract change requires a Change Request to Chat 6. Slice-local internal models may evolve independently as long as adapters preserve canonical contracts.
