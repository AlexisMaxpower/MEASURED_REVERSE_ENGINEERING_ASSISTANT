# MREA SOLIDWORKS 2026 CAD Agent

Pass 2 vendor worker for Chat 4 / Side Chat 4B. This process is intentionally out-of-process from the Python/canonical runtime.

## Baseline

- Windows 11 x64
- SOLIDWORKS 2026 x64
- C# / .NET Framework 4.8
- x64 process
- STA entry point
- official locally installed `SolidWorks.Interop.*` assemblies

No SOLIDWORKS DLL is committed to this repository.

## Protocol

One-shot invocation:

```text
Mrea.SolidWorksCadAgent.exe --request request.json --response response.json
```

The request/response schema is slice-local (`mrea.solidworks-agent.v1`) and does not modify MREA canonical contracts.

## Vendor worker support

Geometry:

- `POINT`
- `LINE`
- `CIRCLE`
- `ARC`

Verified dimensions currently transferred by the worker:

- `DISTANCE` on one line
- `DISTANCE` between two circle/arc centers
- `DIAMETER`
- `RADIUS`

Safe canonical relations supported by the C# worker:

- `HORIZONTAL`
- `VERTICAL`
- `PARALLEL`
- `PERPENDICULAR`
- `TANGENT`
- `CONCENTRIC`
- `EQUAL`
- `COINCIDENT` only when expressed as one explicit `POINT` plus one line/curve

The worker explicitly rejects mappings whose canonical semantics are insufficient:

- `ANGLE` dimension: current contract does not select the angular branch/quadrant;
- endpoint-to-endpoint `COINCIDENT`: endpoint identity is not present in `SketchPackage v1`;
- `SYMMETRIC`: the symmetry-axis role is not identified;
- `UNRESOLVED` constraints.

No unsupported case is silently approximated.

## Primary Chat 4 boundary

The Primary Chat 4 Python `SolidWorksAgentAdapter` currently keeps the Pass 2 golden preflight limited to LINE/CIRCLE, no constraints, and DISTANCE/DIAMETER/RADIUS.

Side Chat 4B does not weaken that boundary. New vendor capabilities are exercised by the separate direct smoke runner:

```powershell
..\scripts\run_solidworks_vendor_extended.ps1 `
  -Agent ".\bin\Release\Mrea.SolidWorksCadAgent.exe" `
  -OutputDir "..\artifacts\solidworks-vendor-extended"
```

Primary Chat 4 may integrate POINT/ARC/constraints after reviewing `SOLIDWORKS_SIDE_HANDOFF.md`.

## Build

Use `../scripts/build_solidworks_agent.ps1`. The build points MSBuild at the local SOLIDWORKS 2026 API interop directory (normally under the installation's `api\redist`).

Real-host status remains `UNVERIFIED` until the worker is actually built and executed on Windows 11 x64 + SOLIDWORKS 2026 x64.
