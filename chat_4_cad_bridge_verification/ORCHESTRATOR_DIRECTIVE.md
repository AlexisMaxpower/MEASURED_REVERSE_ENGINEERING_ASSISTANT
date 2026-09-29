# ORCHESTRATOR DIRECTIVE — Chat 4
**Revision:** OD-2026-09-29-002  
**Pass:** 2  
**Owner:** Chat 6  
**Round 1 verdict:** ACCEPTED FOR GENERIC CAD GATE

Read before Pass 2 implementation.

## Branch policy

Pass 2 work MUST be performed on:

`chat-4/pass-2`

Do not commit Pass 2 implementation directly to `main`.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/sketch_package_v1.json`
- `tests/fixtures/contracts/cad_package_v1.json`

## Canonical output
- `tests/fixtures/contracts/cad_verification_v1.json`

## Accepted baseline

The generic CAD boundary from Pass 1 is accepted structurally:

```text
SketchPackage
→ mapping
→ CadAdapter
→ normalized read-back
→ VerificationEngine
→ CADPackage / CADVerificationReport
```

Keep TEST_DOUBLE and generic SVG/DXF tests independent from a real SOLIDWORKS installation.

## SOLIDWORKS environment decision

`CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` is resolved by:

`chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`

Baseline:

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- C#;
- .NET Framework 4.8 for first adapter baseline;
- out-of-process user-session CAD Agent/worker;
- dedicated STA COM context;
- official locally installed SOLIDWORKS 2026 interop/API SDK references;
- do not commit proprietary SOLIDWORKS binaries;
- real integration verification requires a Windows + SOLIDWORKS 2026 host.

## Pass 2 priority — real adapter skeleton and first verified slice

Implement the real vendor adapter behind the existing `CadAdapter` semantics in stages.

First target:

1. C# project/agent skeleton aligned with ADR-001;
2. connect/attach or explicitly launch SOLIDWORKS 2026;
3. create a new part document;
4. create FRONT sketch;
5. map the minimum golden v1 entities needed by current canonical fixture;
6. create supported verified dimensions;
7. preserve `dimension_id ↔ measurement_id ↔ vendor_dimension_ref`;
8. read values back;
9. normalize to mm/deg;
10. feed existing verification semantics;
11. save/register native artifact through existing CADPackage/artifact boundary.

## Preflight safety requirement

Before a production/vendor transfer can be called verified, check unresolved input relevant to verified dimensions. A real vendor adapter must not claim successful verification when a required verified dimension could not be bound because geometry is unresolved.

Do not silently approximate unsupported constraints/features.

## Testing

- keep existing generic/test-double suite green;
- add pure mapping tests for the SOLIDWORKS adapter boundary where possible without COM;
- provide a Windows/SOLIDWORKS smoke-test command/script/instructions;
- if real host execution is unavailable, report `UNVERIFIED`, never PASS.

## Do not

- move vendor-specific types into canonical contracts;
- replace dimension_id with vendor object identity;
- change numerical transfer tolerance into manufacturing tolerance;
- build a Windows service for v1;
- require SOLIDWORKS for ordinary unit/contract tests.

## Acceptance target

Codebase contains a coherent SOLIDWORKS 2026 CAD Agent implementation path behind the existing adapter boundary, plus an executable real-host smoke/golden procedure. Real-host status must be stated exactly.

## Required handoff

Update `ORCHESTRATOR_HANDOFF.md` with Pass 2 branch, final SHA, exact tests executed, real-host status, limitations and requested acceptance gate.
