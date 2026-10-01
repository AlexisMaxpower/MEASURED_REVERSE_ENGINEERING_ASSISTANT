# MREA SOLIDWORKS 2026 CAD Agent

Out-of-process SOLIDWORKS vendor worker owned by Chat 4.

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

Protocol identifier:

```text
mrea.solidworks-agent.v1
```

The request carries two fail-closed compatibility fingerprints:

- `worker_capabilities_sha256` — the declared Python/C# worker capability projection;
- `constraint_capabilities_sha256` — the narrower constraint capability contract.

Both are checked before SOLIDWORKS COM startup. Pass 13 also validates the fingerprinted verified-dimension shape rules in the request envelope before COM startup.

The response records vendor-runtime facts used by Primary Chat 4 runtime evidence:

- `real_host_executed`;
- actual `solidworks_version` from `RevisionNumber()`;
- stable `exit_code`;
- machine-readable `diagnostics`;
- dimension bindings;
- normalized read-back;
- native artifacts.

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

## Fail-closed startup and request envelope

Before opening SOLIDWORKS, the worker validates:

1. protocol and adapter identity;
2. full worker and constraint capability fingerprints;
3. required request identity/output fields;
4. dimension IDs and referenced entity IDs;
5. no duplicate entity IDs within a dimension;
6. dimension-specific units;
7. supported dimension/entity patterns;
8. ANGLE range and non-parallel LINE geometry.

Only after those checks does `SolidWorksSession.Open(request)` attach to or launch SOLIDWORKS.

The session then:

1. reads `RevisionNumber()` and requires the project SOLIDWORKS 2026 revision-major baseline;
2. resolves an explicit or configured part template;
3. creates a new part and opens a FRONT-plane sketch;
4. cleans COM/document state if startup fails before a session object is returned.

A version mismatch is an agent startup failure, never a successful transfer.

## Current declared geometry and constraint slice

Geometry entities:

- `POINT`;
- `LINE`;
- `CIRCLE`;
- `ARC`.

Fail-closed verified constraints:

- `HORIZONTAL`;
- `VERTICAL`;
- `PARALLEL`;
- `PERPENDICULAR`;
- `CONCENTRIC`;
- `EQUAL` for LINE/LINE;
- `TANGENT` for supported LINE/CIRCLE/ARC pairs with at least one CIRCLE/ARC.

`COINCIDENT` and `SYMMETRIC` remain unsupported because the canonical relation payload does not currently carry enough sub-entity/axis role information for a deterministic mapping.

## Verified dimension slice

Pass 13 makes the shape rules explicit and fingerprinted:

| Dimension | Unit | Supported entity pattern |
| --- | --- | --- |
| `DISTANCE` | `mm` | one `LINE`, or two `CIRCLE`/`ARC` entities for center distance |
| `DIAMETER` | `mm` | exactly one `CIRCLE` |
| `RADIUS` | `mm` | exactly one `CIRCLE` or `ARC` |
| `ANGLE` | `deg` | exactly two non-parallel `LINE` entities, with `0 < value < 180` |

Duplicate entity IDs inside one verified dimension fail closed.

The machine-readable source is `src/mrea_cad_bridge/solidworks_dimension_capabilities.py`. Python preflight and the C# request envelope are tested against that declared subset.

## Build

```powershell
.\scripts\build_solidworks_agent.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"
```

The build script finds MSBuild from `PATH` or Visual Studio Installer/`vswhere`, requires official SOLIDWORKS interop assemblies, builds x64, and fails closed if the expected executable is absent.

## Controlled host validation

The existing one-command host procedure remains:

```powershell
.\scripts\run_solidworks_pass3_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir ".\artifacts\solidworks-pass3"
```

It executes host readiness, build/agent discovery, real-host transfer, canonical read-back verification, native artifact hash verification, and the side-local runtime-input bundle used by Primary Chat 4.

A successful side run may report canonical verification and readiness for Primary evaluation, but it must not infer final real-host runtime `VERIFIED`. Primary Chat 4 owns `mrea.cad-runtime-evidence.v1` and the final runtime verdict.

Without an actual supported Windows 11 x64 + SOLIDWORKS 2026 x64 execution, real-host status remains `UNVERIFIED`.
