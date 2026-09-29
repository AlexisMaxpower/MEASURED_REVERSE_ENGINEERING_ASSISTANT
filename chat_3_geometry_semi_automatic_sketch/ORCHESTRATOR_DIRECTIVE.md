# ORCHESTRATOR DIRECTIVE — Chat 3
**Revision:** OD-2026-09-29-001  
**Owner:** Chat 6

Your canonical-contract blocker is removed for the v1 FRONT baseline.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`

## Canonical output
- `tests/fixtures/contracts/sketch_package_v1.json`

## v1 required geometry
- POINT
- LINE
- CIRCLE
- ARC

Sketch coordinates: `MAT_XY_MM`.

## Current directive
Implement deterministic FRONT flow:
fixture → primitives → GeometryGraph → measurement binding → conflict detection → minimal constraints → SketchPackage → golden test.

Verified measurements are hard truth. Unsupported/ambiguous geometry goes to `unresolved`.

## Next acceptance target
Reproduce a schema-valid deterministic SketchPackage with preserved `measurement_id` links.

Do not expand v1 geometry vocabulary without Change Request.
