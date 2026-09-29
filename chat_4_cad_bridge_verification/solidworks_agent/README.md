# MREA SOLIDWORKS 2026 CAD Agent

Vendor worker for Chat 4 / Side Chat 4B. The process is intentionally out-of-process from the Python/canonical runtime.

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

The current canonical golden slice supports:

- `LINE`
- `CIRCLE`
- `DISTANCE` on one line
- `DISTANCE` between two circle centers
- `DIAMETER`
- `RADIUS`

POINT/ARC, ANGLE, and canonical constraints remain blocked by the Primary Chat 4 Python preflight in the integrated path rather than silently approximated.

## Pass 4 runtime diagnostics

The worker now records:

- `real_host_executed`;
- actual SOLIDWORKS `RevisionNumber()`;
- stable process `exit_code`;
- machine-readable diagnostics with `code`, `stage`, `message`, `severity`, and optional `details`;
- structured error metadata using the same stable fields.

The agent also fail-closes if the attached/launched SOLIDWORKS revision is not the 2026 adapter baseline (revision major `34`).

### Exit classes

```text
0   completed successfully
20  invalid request / protocol / input
30  SOLIDWORKS COM startup or supported-version failure
40  CAD transfer / rebuild / read-back failure
50  native artifact or response-write failure
70  unexpected internal failure
```

The separate host-preflight/one-command wrapper uses exit `10` when the Windows/SOLIDWORKS host is not READY before agent execution.

## Host-readiness gate

Use:

```powershell
..\scripts\test_solidworks_host_readiness.ps1
```

to generate slice-local `mrea.cad-host-readiness.v1` evidence. Required unknown facts are `UNVERIFIED`, never `PASS`.

For the complete controlled path use:

```powershell
..\scripts\run_solidworks_real_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir "..\artifacts\solidworks-real-host"
```

The wrapper performs fail-closed readiness, builds/locates the agent, runs the canonical golden transfer, writes the native `.SLDPRT`, and emits Primary Chat 4 runtime evidence.

## Build

Use `../scripts/build_solidworks_agent.ps1`. It resolves MSBuild from `PATH` or Visual Studio Installer/`vswhere` and points MSBuild at the local SOLIDWORKS 2026 API interop directory (normally under the installation's `api\redist`).
