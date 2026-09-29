# MREA SOLIDWORKS 2026 CAD Agent

Out-of-process vendor worker for Chat 4 / Side Chat 4B.

## Supported host baseline

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- C# / .NET Framework 4.8;
- x64 STA process;
- official locally installed `SolidWorks.Interop.*` assemblies.

No SOLIDWORKS DLL is committed to this repository.

## Process protocol

```text
Mrea.SolidWorksCadAgent.exe --request request.json --response response.json
```

Protocol identifier remains:

```text
mrea.solidworks-agent.v1
```

The response now also records vendor-runtime facts required by Pass 3:

- `real_host_executed`;
- actual `solidworks_version` from `RevisionNumber()`;
- stable `exit_code`;
- machine-readable `diagnostics`;
- existing bindings, normalized read-back and native artifacts.

These are slice-local/vendor facts. They do not modify canonical MREA contracts.

## Stable exit classes

```text
0   completed successfully
20  invalid request/protocol/input
30  SOLIDWORKS/COM startup or version failure
40  CAD transfer/rebuild/read-back failure
50  artifact write/evidence failure
70  unexpected internal failure
```

Host preflight is outside the worker and uses exit code `10` when required host readiness is not `READY`.

## Fail-closed SOLIDWORKS startup

The worker:

1. attaches to `SldWorks.Application` when allowed;
2. otherwise launches it when allowed;
3. reads `RevisionNumber()`;
4. requires the project SOLIDWORKS 2026 revision-major baseline;
5. resolves an explicit or configured part template;
6. creates a new part and opens a FRONT-plane sketch;
7. cleans COM/document state if startup fails before a session object is returned.

A version mismatch is an agent startup failure, never a successful transfer.

## Current geometric transfer slice

The existing Pass-2 real-host geometry remains intentionally unchanged in this Pass-3 fix:

- `LINE`;
- `CIRCLE`;
- `DISTANCE` on one line;
- `DISTANCE` between two circle centers;
- `DIAMETER`;
- `RADIUS`.

POINT/ARC/ANGLE/additional constraints are not expanded here because Pass 3 is about truthful host readiness and runtime evidence production.

## Build

```powershell
.\scripts\build_solidworks_agent.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"
```

The build script finds MSBuild from `PATH` or Visual Studio Installer/`vswhere`, requires the official SOLIDWORKS interop assemblies, builds x64 and fails closed if the expected executable is absent.

## Pass-3 controlled host producer

Use the one-command procedure:

```powershell
.\scripts\run_solidworks_pass3_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir ".\artifacts\solidworks-pass3"
```

It runs:

```text
host readiness -> build/locate agent -> host readiness -> agent transfer
-> canonical read-back verification -> native artifact hash re-check
-> evidence-input bundle for Primary Chat 4
```

A successful side run may print:

```text
CANONICAL_CAD_VERIFICATION=VERIFIED
SIDE_HOST_EVIDENCE=READY_FOR_PRIMARY_EVALUATION
FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4
```

It must **not** print or infer final real-host runtime `VERIFIED`. Primary Chat 4 owns `mrea.cad-runtime-evidence.v1` and the final runtime verdict.

Without an actual supported Windows/SOLIDWORKS execution, real-host status remains `UNVERIFIED`.
