# MREA SOLIDWORKS 2026 CAD Agent

Pass 2 vendor worker for Chat 4. This process is intentionally out-of-process from the Python/canonical runtime.

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

The current real-host acceptance slice supports:

- `LINE`
- `CIRCLE`
- `DISTANCE` on one line
- `DISTANCE` between two circle centers
- `DIAMETER`
- `RADIUS`

POINT/ARC, ANGLE, and canonical constraints are rejected before a real transfer in this Pass 2 slice rather than approximated.

## Build

Use `../scripts/build_solidworks_agent.ps1`. The build points MSBuild at the local SOLIDWORKS 2026 API interop directory (normally under the installation's `api\redist`).
