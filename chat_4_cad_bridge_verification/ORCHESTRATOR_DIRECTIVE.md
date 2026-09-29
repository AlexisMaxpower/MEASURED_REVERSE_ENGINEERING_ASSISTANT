# ORCHESTRATOR DIRECTIVE — Chat 4
**Revision:** OD-2026-09-29-001  
**Owner:** Chat 6

The shared-contract blocker is removed for verification-core/generic-export work.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/sketch_package_v1.json`
- `tests/fixtures/contracts/cad_package_v1.json`

## Canonical output
- `tests/fixtures/contracts/cad_verification_v1.json`

## v1 transfer policy
CAD verification checks numerical transfer, not manufacturing tolerance:
- `1e-6 mm`
- `1e-6 deg`

## Current directive
Implement pure verification core first without SOLIDWORKS:
expected dimensions + normalized CAD read-back → VerificationReport.

Then generic SVG/DXF for the v1 entity subset. SOLIDWORKS C# adapter follows after the pure boundary is tested.

## Next acceptance target
Golden fixture gives four VERIFIED results. Negative tests cover MISMATCH and MISSING.
