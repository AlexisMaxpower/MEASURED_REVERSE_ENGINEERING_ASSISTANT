# ORCHESTRATOR DIRECTIVE — Chat 1
**Revision:** OD-2026-09-29-001  
**Owner:** Chat 6

Read before the next coding iteration.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/project_v1.json`
- `tests/fixtures/contracts/capture_package_v1.json`

## Current directive
Existing internal Project/Capture models remain valid slice internals. Add an outward contract adapter/builder that produces canonical:
- `ProjectContract v1`;
- `CapturePackage v1`.

Reconcile:
- canonical boundary requires stable `part_id`;
- contract IDs are opaque strings;
- CapturePackage owns clean reference artifact, measurement frames and optional calibration per view.

Do not copy shared schemas into Chat 1.

## Next acceptance target
For one FRONT view, produce a schema-valid canonical CapturePackage.

## Do not
- redefine `CapturePackage`;
- modify `core/contracts`;
- change measurement semantics.
