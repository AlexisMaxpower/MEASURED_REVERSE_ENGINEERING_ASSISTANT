# SOLIDWORKS SIDE HANDOFF — Chat 4B → Primary Chat 4

**Pass:** 2  
**Directive revision:** `OD-2026-09-29-002`  
**Branch:** `chat-4b/pass-2`  
**Accepted common baseline:** `158a53e5751de00d0dc0a960fb95f68aceab7310`  
**Final implementation SHA before this handoff metadata commit:** `3883a393000d5dc412b6edb5bd3cedc56b349689`  
**Date:** 2026-09-29

## Status

`READY_FOR_PRIMARY_CHAT_4_REVIEW`

Real SOLIDWORKS host: **UNVERIFIED**.

C# production compilation against official SOLIDWORKS 2026 interop: **UNVERIFIED** — the current execution environment has no Windows/.NET Framework/MSBuild/SOLIDWORKS interop toolchain.

## Implemented

Vendor-specific C# CAD Agent was extended without changing canonical contracts or Primary Chat 4 Python/domain semantics.

Implemented:

- vendor protocol DTO support for `POINT`, `ARC`, and canonical constraint DTOs;
- request validation before starting/attaching SOLIDWORKS COM;
- native `POINT` creation;
- native counter-clockwise `ARC` creation from canonical center/radius/start/end angles;
- safe sketch-relation creation through the active sketch relation manager;
- explicit validation of relation/entity combinations;
- explicit rejection of ambiguous mappings instead of approximation;
- solver-status read-back and conservative propagation to `constraint_conflicts`;
- stronger dimension/entity type guards;
- explicit rebuild failure handling;
- direct vendor-only extended smoke runner with native artifact and SHA-256 verification;
- vendor-specific Build/Reuse and implementation documentation.

## Changed files

Modified:

```text
chat_4_cad_bridge_verification/solidworks_agent/ProtocolModels.cs
chat_4_cad_bridge_verification/solidworks_agent/Program.cs
chat_4_cad_bridge_verification/solidworks_agent/SolidWorksTransfer.cs
chat_4_cad_bridge_verification/solidworks_agent/README.md
```

Added:

```text
chat_4_cad_bridge_verification/scripts/run_solidworks_vendor_extended.py
chat_4_cad_bridge_verification/scripts/run_solidworks_vendor_extended.ps1
chat_4_cad_bridge_verification/docs/BUILD_REUSE_CHECK_SOLIDWORKS_VENDOR_EXTENSIONS.md
chat_4_cad_bridge_verification/docs/SOLIDWORKS_VENDOR_EXTENSIONS_PASS_2.md
chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md
```

No changes were made to:

```text
core/contracts/
tests/fixtures/contracts/
chat_4_cad_bridge_verification/src/mrea_cad_bridge/
```

## SOLIDWORKS API calls used

New/extended vendor mapping uses:

- `ISketchManager.CreatePoint`;
- `ISketchManager.CreateArc`;
- active `ISketch.RelationManager`;
- `ISketchRelationManager.AddRelation`;
- `ISketch.GetConstrainedStatus`;
- existing `CreateLine` / `CreateCircleByRadius`;
- existing `AddDimension2` / `AddDiameterDimension2` / `AddRadialDimension2`;
- existing dimension `SetSystemValue3` / `GetSystemValue3`;
- existing native `SaveAs`.

## Unit conversions

Canonical boundary remains unchanged:

```text
length: mm
angle: deg
```

SOLIDWORKS vendor layer remains:

```text
length: m
angle: rad
```

New `POINT` and `ARC` geometry performs `mm → m` conversion before SOLIDWORKS calls.

No canonical values are silently rounded or rewritten.

## Entity support

Vendor worker after this pass:

```text
POINT   implemented
LINE    implemented (existing)
CIRCLE  implemented (existing)
ARC     implemented
```

Canonical ARC convention is preserved as positive counter-clockwise sweep. `CreateArc` is called with positive direction.

A zero/full-circle ARC span is explicitly rejected; a full circle must be represented as `CIRCLE`.

## Dimension support

Vendor worker:

```text
DISTANCE  implemented for existing supported shapes
DIAMETER  implemented
RADIUS    implemented, including ARC
ANGLE     intentionally blocked
```

`ANGLE` is not approximated. `SketchPackage v1` identifies involved entities and numeric value but does not identify the angular branch/quadrant/endpoint selection required for deterministic SOLIDWORKS angular-dimension placement.

## Constraint support

Safely mapped by the worker:

```text
HORIZONTAL
VERTICAL
PARALLEL
PERPENDICULAR
TANGENT
CONCENTRIC
EQUAL
COINCIDENT — only explicit POINT + LINE/CIRCLE/ARC
```

Explicitly rejected:

```text
COINCIDENT between unspecified line endpoints
SYMMETRIC without an identified symmetry-axis role
UNRESOLVED constraints
unsupported entity/relation combinations
```

Reason: current canonical `SketchConstraint` contains `constraint_id`, `type`, `entity_ids`, `status`, but no endpoint-role or symmetry-axis-role field. Side Chat 4B does not infer those missing semantics.

## Solver / conflict behavior

After geometry, relations and dimensions are created, the worker reads `GetConstrainedStatus()`.

- under-constrained / fully-constrained: normal read-back continues;
- over-constrained / no-solution / invalid-solution: all requested verified dimension IDs are returned in `constraint_conflicts`;
- unknown constraint / autosolve off: adapter failure.

This is deliberately conservative so vendor solver failure cannot become verification success.

## Artifact behavior

Existing behavior is preserved:

- native `.SLDPRT` is written under the requested controlled output directory;
- response includes artifact id, kind, URI, media type, SHA-256 and vendor metadata;
- no new storage architecture was introduced.

The new vendor smoke runner independently verifies the returned SHA-256 against the generated `.SLDPRT`.

## Pure/static checks executed

Executed in the available Linux environment:

```text
- Python AST parse: run_solidworks_vendor_extended.py — PASS
- runner --help execution — PASS
- C# source delimiter/structure sanity check on modified DTO/Program/Transfer files — PASS
- official SOLIDWORKS 2026 API documentation checked for relation manager, constraint enums and solver statuses
```

No existing generic Chat 4 Python test was modified.

The full generic test suite was not re-executed in this side-chat environment because this pass does not alter the Primary Python/domain layer and no repository checkout/test toolchain was available here.

## C# compilation

```text
UNVERIFIED
```

Reason: current host has no `dotnet`, `msbuild`, `xbuild`, `mcs`, or `csc`, and does not have the official SOLIDWORKS 2026 interop assemblies.

No compilation PASS is claimed.

## Real SOLIDWORKS host

```text
UNVERIFIED
```

Required host remains:

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- .NET Framework 4.8/MSBuild;
- official SOLIDWORKS 2026 interop assemblies;
- interactive user-session desktop.

Extended vendor acceptance command:

```powershell
cd chat_4_cad_bridge_verification

.\scripts\build_solidworks_agent.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"

.\scripts\run_solidworks_vendor_extended.ps1 `
  -Agent ".\solidworks_agent\bin\Release\Mrea.SolidWorksCadAgent.exe" `
  -OutputDir ".\artifacts\solidworks-vendor-extended"
```

Acceptance marker:

```text
VENDOR_EXTENDED_RESULT=VERIFIED
```

Until that command succeeds on the supported host, these vendor extensions are not real-host verified.

## Known limitations

1. Primary Chat 4 Python preflight still intentionally blocks `POINT`, `ARC`, and all constraints, so the new capabilities are currently reachable only by the direct vendor protocol/smoke runner.
2. `ANGLE` is blocked because deterministic angular branch semantics are missing.
3. Endpoint-to-endpoint `COINCIDENT` is blocked when endpoint identity is not explicit.
4. `SYMMETRIC` is blocked because the symmetry-axis role is not identified.
5. Constraint-conflict reporting is conservative at sketch level; a solver conflict marks all requested verified dimensions as conflict rather than attempting unsupported per-dimension root-cause attribution.
6. Real C# build and SOLIDWORKS execution remain unverified.

## Open technical questions

### Q1 — ANGLE canonical semantics

Primary Chat 4 / Chat 6 should decide whether current upstream geometry guarantees a deterministic angular branch, or whether the shared contract eventually needs a vendor-neutral angular selector/anchor.

### Q2 — endpoint identity for COINCIDENT

If Chat 3 needs endpoint-to-endpoint coincidence, current `entity_ids` alone do not specify `start` vs `end` for a LINE. Do not add vendor-specific endpoint fields; resolve at canonical/integration level if required.

### Q3 — symmetry-axis role

`SYMMETRIC` needs a deterministic way to identify which referenced entity is the axis. Current unordered role semantics are insufficient for the vendor worker.

## Requested integration action

Primary Chat 4 should review this branch and, if accepted:

1. extend its `SolidWorksAgentAdapter` process request to pass canonical `constraints`;
2. widen its vendor preflight from `LINE/CIRCLE` to `POINT/LINE/CIRCLE/ARC`;
3. retain explicit rejection of unsupported/ambiguous constraints;
4. keep `ANGLE` blocked until Q1 is resolved;
5. add/adjust Primary-owned Python boundary tests for POINT/ARC/constraints;
6. run generic regression after integration;
7. run both the existing golden smoke and the 4B extended smoke on the real supported host when available.

No shared-contract Change Request is submitted by Side Chat 4B in this pass. The three semantic gaps above are reported to Primary Chat 4 for integration-level disposition.
