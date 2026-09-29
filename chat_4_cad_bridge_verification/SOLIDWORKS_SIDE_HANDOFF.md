# SOLIDWORKS SIDE HANDOFF — Chat 4B → Primary Chat 4

**Pass:** 4  
**Latest published orchestrator directive:** `OD-2026-09-29-003`  
**Branch:** `chat-4b/pass-4`  
**Primary baseline:** `chat-4/pass-3` @ `8e5c6c503f9bf7f7420b8f6b99d71797d3073d38`  
**Implementation SHA before this handoff metadata commit:** `2e566ab89ac780c4d99d8a5e97c6ed975579500e`  
**Date:** 2026-09-29

## Status

`READY_FOR_PRIMARY_CHAT_4_REVIEW`

```text
C# COMPILE      = UNVERIFIED
REAL_HOST       = UNVERIFIED
GITHUB_CONTENT  = VERIFIED_AFTER_HANDOFF_BY_SIDE_CHAT_4B
```

Pass 4 is a user-directed continuation because no `OD-004` had been published when the pass started. The work closes the still-pending Side Chat 4B portion of `OD-003`: controlled Windows/SOLIDWORKS host readiness and truthful real-host evidence production.

## Source-of-truth recovery

Before implementation Side Chat 4B verified:

- `main` still published `OD-2026-09-29-003`;
- `chat-4b/pass-3` contained only the assigned Pass 3 task and no implementation/handoff;
- Primary `chat-4/pass-3` implemented `mrea.cad-host-readiness.v1` parsing/aggregation and `mrea.cad-runtime-evidence.v1` semantics;
- Primary progress explicitly marked the Side Chat 4B host/runtime half as pending.

Therefore `chat-4b/pass-4` was created from the actual Primary Pass 3 head, not from stale `main` or the incomplete Side Pass 3 branch.

## Implemented

### 1. Fail-closed Windows/SOLIDWORKS host readiness

Added `scripts/test_solidworks_host_readiness.ps1` producing Primary-compatible:

```text
mrea.cad-host-readiness.v1
```

Checks:

```text
OS_WINDOWS_11_X64
PROCESS_X64
DOTNET_FRAMEWORK_48
AGENT_EXECUTABLE_AVAILABLE
SOLIDWORKS_COM_REGISTERED
SOLIDWORKS_VERSION_2026
SOLIDWORKS_INTEROP_AVAILABLE
OUTPUT_PATH_WRITABLE
PART_TEMPLATE_AVAILABLE
```

Optional build-only check:

```text
MSBUILD_AVAILABLE
```

Unknown required facts remain `UNVERIFIED`; any required `FAIL` remains `FAILED`; only all required `PASS` becomes `READY`.

### 2. Actual SOLIDWORKS version identity

Both host readiness and the C# worker query:

```text
ISldWorks::RevisionNumber()
```

The current narrow SOLIDWORKS 2026 project baseline uses revision major `34`. A different or unparsable revision fails closed.

The raw revision string is preserved as runtime evidence input rather than replaced by an inferred marketing-version string.

### 3. Stable worker diagnostics and exit classes

The slice-local `mrea.solidworks-agent.v1` response now carries:

```text
real_host_executed
solidworks_version
exit_code
diagnostics[]
error.code
error.stage
error.severity
error.details
```

Stable exit classes:

```text
0   success
20  invalid request/protocol/input
30  SOLIDWORKS COM startup/version failure
40  CAD transfer/rebuild/read-back failure
50  native artifact/response persistence failure
70  unexpected internal failure
```

Host wrapper owns:

```text
10  host/build readiness not READY
```

### 4. COM lifecycle hardening

`SolidWorksSession.Open()` now owns cleanup for failures that occur after COM attach/launch but before a usable `SolidWorksSession` is returned.

If startup fails:

- partially created model is closed/released where possible;
- attached user SOLIDWORKS session is never terminated;
- only an instance launched by the agent for the failed startup may receive `ExitApp()`;
- COM references are deterministically released where practical.

This closes the previous leak path for version/template/front-plane/start-sketch failures.

### 5. Build readiness

`build_solidworks_agent.ps1` now resolves MSBuild through:

1. `PATH`;
2. Visual Studio Installer `vswhere.exe` fallback.

It fail-closes if:

- official SOLIDWORKS interop DLLs are missing;
- MSBuild cannot be resolved;
- MSBuild returns non-zero;
- expected x64 agent executable does not exist after build.

No proprietary SOLIDWORKS DLL is added to the repository.

### 6. One-command controlled real-host path

Added:

```text
scripts/run_solidworks_real_host_validation.ps1
scripts/run_solidworks_real_host_validation.py
```

Windows entry point:

```powershell
.\scripts\run_solidworks_real_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir ".\artifacts\solidworks-real-host"
```

Flow:

```text
host preflight
→ build/locate agent
→ final host preflight
→ canonical golden SketchPackage
→ existing Primary SolidWorksAgentAdapter
→ C# x64 STA Agent
→ SOLIDWORKS 2026 COM
→ native .SLDPRT
→ normalized read-back
→ existing VerificationEngine
→ CADPackage + CADVerificationReport
→ existing Primary build_runtime_evidence()
```

The wrapper prints `REAL_HOST_GATE=VERIFIED` only after Primary runtime evidence returns `status = VERIFIED`.

### 7. Host/readiness artifacts

Controlled run writes:

```text
host_readiness.json
<sketch_package_id>.SLDPRT
cad_package.json
cad_verification.json
runtime_evidence.json
```

If the agent needs to be built first it can also write:

```text
host_readiness_prebuild.json
```

## Changed files

Modified:

```text
chat_4_cad_bridge_verification/solidworks_agent/Program.cs
chat_4_cad_bridge_verification/solidworks_agent/ProtocolModels.cs
chat_4_cad_bridge_verification/solidworks_agent/README.md
chat_4_cad_bridge_verification/solidworks_agent/SolidWorksSession.cs
chat_4_cad_bridge_verification/scripts/build_solidworks_agent.ps1
```

Added:

```text
chat_4_cad_bridge_verification/scripts/test_solidworks_host_readiness.ps1
chat_4_cad_bridge_verification/scripts/run_solidworks_real_host_validation.py
chat_4_cad_bridge_verification/scripts/run_solidworks_real_host_validation.ps1
chat_4_cad_bridge_verification/docs/BUILD_REUSE_CHECK_SOLIDWORKS_HOST_VALIDATION.md
chat_4_cad_bridge_verification/docs/SOLIDWORKS_REAL_HOST_VALIDATION_PASS_4.md
chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md
```

Not modified:

```text
core/contracts/
tests/fixtures/contracts/
.github/workflows/
chat_4_cad_bridge_verification/src/mrea_cad_bridge/
chat_4_cad_bridge_verification/tests/
```

## Verification performed

### Repository / ownership

Compared `chat-4b/pass-4` against Primary baseline:

```text
8e5c6c503f9bf7f7420b8f6b99d71797d3073d38
```

Before handoff the diff contained only Side Chat 4B-owned SOLIDWORKS worker/scripts/docs paths. No shared contract, Primary runtime-evidence implementation, canonical fixture, or CI file was changed.

### Python runner

A byte-for-byte implementation copy of the Pass 4 Python runner was checked in the available execution environment with:

```text
python -m py_compile
--help invocation
```

Result:

```text
PASS
PASS
```

### Available toolchain probe

The current execution environment was checked for:

```text
dotnet
msbuild
csc
mcs
xbuild
pwsh
powershell
```

All are unavailable on this Linux host.

Therefore no C# compilation or PowerShell execution is represented as PASS.

### Official API sanity check

SOLIDWORKS API documentation was checked for:

- `ISldWorks::RevisionNumber()` as the runtime version source;
- `ISldWorks::GetBuildNumbers2()` as version/build metadata;
- default part-template access through SOLIDWORKS user preferences.

These checks support the API choice but do not substitute for a real SOLIDWORKS 2026 run.

## C# compile status

```text
UNVERIFIED
```

Reason: no Windows/.NET Framework/MSBuild/SOLIDWORKS interop build host is connected to this chat execution environment.

## Real-host status

```text
UNVERIFIED
```

Required acceptance host:

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- .NET Framework 4.8;
- official SOLIDWORKS 2026 interop assemblies;
- interactive user desktop;
- Python environment capable of running Primary Chat 4 package.

No inferred or simulated runtime PASS is claimed.

## Known limitations

1. Primary `src/mrea_cad_bridge/solidworks_agent.py` intentionally remains unchanged by Side Chat 4B. It currently ignores the new backward-compatible response metadata (`exit_code`, diagnostics, `solidworks_version`) when it converts the worker response to `CadAdapterResult`.
2. Therefore a Primary-path worker failure currently reaches the canonical adapter layer mainly through its error message, while the direct worker response has richer stable diagnostics.
3. C# syntax/interop compatibility must still be proven by the supported Windows build host.
4. PowerShell scripts must still be executed on Windows PowerShell/PowerShell on the supported host.
5. Real SOLIDWORKS COM lifecycle, revision identity, native SaveAs, read-back, and runtime evidence remain unverified until the controlled command succeeds.

## Requested Primary Chat 4 integration action

1. Review the Pass 4 side diff without changing canonical semantics.
2. Preserve Primary ownership of `runtime_evidence.py` and VerificationEngine.
3. Decide whether to propagate worker `diagnostics/exit_code/solidworks_version` through a slice-local Primary metadata/error transport; no shared-contract change is required for the current controlled runner.
4. Run the complete generic Chat 4 regression and canonical integration gates after integration.
5. On the supported Windows/SOLIDWORKS host run the one-command real-host gate.
6. Do not mark real runtime VERIFIED unless `runtime_evidence.json` is VERIFIED and the native artifact/read-back evidence is present.

## GitHub publication gate

Per project-owner instruction, Side Chat 4B must not rely on successful write responses. After publishing this handoff it will:

1. fetch the branch head from GitHub;
2. compare it against the Primary baseline;
3. fetch every Pass 4 delta file from `chat-4b/pass-4`;
4. verify the final handoff exists on that branch;
5. retry any missing/stale file write and repeat the checks before reporting completion.
