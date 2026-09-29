# SOLIDWORKS 2026 vendor extension state — Chat 4B / Pass 2

## Scope

Этот документ описывает только vendor-specific слой C# CAD Agent.

Canonical contracts и Python verification semantics не изменяются.

## Entity mapping

| Canonical entity | SOLIDWORKS API | Status |
|---|---|---|
| `POINT` | `ISketchManager.CreatePoint` | implemented in 4B |
| `LINE` | `ISketchManager.CreateLine` | existing |
| `CIRCLE` | `ISketchManager.CreateCircleByRadius` | existing |
| `ARC` | `ISketchManager.CreateArc` | implemented in 4B |

### ARC convention

Generic Chat 4 SVG exporter treats:

```text
span = (end_angle_deg - start_angle_deg) mod 360
```

as a positive counter-clockwise sweep.

4B preserves that convention by creating SOLIDWORKS arcs with `Direction = +1`.

A zero/full-circle span is rejected. Full circles must remain `CIRCLE`.

## Constraint mapping

The worker accepts canonical constraint DTOs:

```json
{
  "constraint_id": "K-001",
  "type": "HORIZONTAL",
  "entity_ids": ["L-001"],
  "status": "VERIFIED"
}
```

Mapping uses `ISketch.RelationManager.AddRelation`.

Supported safe mappings:

| Canonical | SOLIDWORKS relation | Vendor rule |
|---|---|---|
| `HORIZONTAL` | `swConstraintType_HORIZONTAL` / `HORIZPOINTS` | line(s), or >=2 explicit points |
| `VERTICAL` | `swConstraintType_VERTICAL` / `VERTPOINTS` | line(s), or >=2 explicit points |
| `PARALLEL` | `swConstraintType_PARALLEL` | exactly 2 lines |
| `PERPENDICULAR` | `swConstraintType_PERPENDICULAR` | exactly 2 lines |
| `TANGENT` | `swConstraintType_TANGENT` | 2 segments, at least one circle/arc |
| `CONCENTRIC` | `swConstraintType_CONCENTRIC` | 2 circles/arcs |
| `EQUAL` | `swConstraintType_SAMELENGTH` | >=2 lines or >=2 circles/arcs |
| `COINCIDENT` | `swConstraintType_COINCIDENT` | only explicit POINT + curve/line |

### Intentionally rejected

`COINCIDENT` between line endpoints is not guessed because `SketchPackage v1` does not identify which endpoint participates.

`SYMMETRIC` is not guessed because `SketchPackage v1` does not identify which `entity_id` is the symmetry axis.

`UNRESOLVED` constraints are rejected.

## Solver safety

After geometry, relations and dimensions are created, the worker calls `GetConstrainedStatus`.

Statuses:

- fully/under constrained: continue;
- over constrained;
- no solution;
- invalid solution;

cause all verified dimensions in the request to be returned in `constraint_conflicts`.

This is intentionally conservative. It prevents a solver failure from becoming `VERIFIED`.

Unknown constraint status or autosolve-off is treated as adapter failure because reliable verification is impossible.

## ANGLE dimension

`ANGLE` remains intentionally blocked in the 4B worker.

Reason:

SOLIDWORKS angular dimension creation can depend on selected endpoint/location/quadrant. `SketchPackage v1` currently contains:

```text
dimension_id
type = ANGLE
value
unit = deg
entity_ids
```

but no branch/quadrant/endpoint selector.

Therefore an automatic mapping could produce a geometrically different angular dimension while still using the same two lines.

Required integration decision belongs to Primary Chat 4 / Chat 6. Possible future approaches:

- define deterministic canonical angular branch semantics;
- add a vendor-neutral angular anchor/selector;
- prove an existing invariant from Chat 3 that removes the ambiguity.

Side Chat 4B does not change the shared contract itself.

## Primary Chat 4 integration action

After review, Primary Chat 4 can independently decide to extend `SolidWorksAgentAdapter` request building/preflight to allow:

- `POINT`;
- `ARC`;
- canonical `constraints`.

Until Primary makes that change, these features are reachable only through the direct vendor protocol / vendor extended smoke runner.

`ANGLE` should remain blocked at the Python preflight until its semantics are resolved.

## Real-host smoke

Build the agent as usual, then run:

```powershell
cd chat_4_cad_bridge_verification

.\scripts\build_solidworks_agent.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"

.\scripts\run_solidworks_vendor_extended.ps1 `
  -Agent ".\solidworks_agent\bin\Release\Mrea.SolidWorksCadAgent.exe" `
  -OutputDir ".\artifacts\solidworks-vendor-extended"
```

Optional:

```powershell
-PartTemplate "C:\path\to\Part.prtdot"
```

Acceptance marker:

```text
VENDOR_EXTENDED_RESULT=VERIFIED
```

This requires a real Windows 11 x64 + SOLIDWORKS 2026 x64 host.

Until actually executed there, status is:

```text
UNVERIFIED
```
