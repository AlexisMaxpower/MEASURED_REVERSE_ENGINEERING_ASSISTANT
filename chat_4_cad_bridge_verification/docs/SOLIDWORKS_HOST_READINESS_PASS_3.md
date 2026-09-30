# SOLIDWORKS 2026 Host Readiness — Side Chat 4B / Pass 3

**Directive:** `OD-2026-09-29-003`  
**Correction source:** `ORCHESTRATOR_FIX_REQUIRED_PASS3.md`  
**Branch:** `chat-4b/pass-3`

## Purpose

This implementation supplies truthful Windows/SOLIDWORKS runtime facts to the Primary Chat 4 runtime-evidence boundary. It does not change canonical contracts and does not decide the final `mrea.cad-runtime-evidence.v1` status.

## Host-readiness output

`test_solidworks_host_readiness.ps1` emits:

```text
mrea.cad-host-readiness.v1
```

Every check contains:

- `code`;
- `status = PASS | FAIL | UNVERIFIED`;
- `message`;
- `required`;
- optional `details`.

Required checks produced by Side Chat 4B:

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

When a build is required, `MSBUILD_AVAILABLE` is also checked. MSBuild discovery checks normal `PATH` and Visual Studio Installer/`vswhere`.

Required `FAIL` makes readiness `FAILED`. Required `UNVERIFIED` makes readiness `UNVERIFIED`. Only all required checks passing produces `READY`.

## SOLIDWORKS version truth

Both preflight and the worker read the actual `SldWorks.Application.RevisionNumber()` value. The worker records it in `solidworks_version` and rejects a revision-major mismatch before CAD transfer.

The version requirement is therefore checked twice at different boundaries:

1. host preflight before transfer;
2. worker session startup immediately before document creation.

This prevents a stale preflight result or different running SOLIDWORKS instance from silently becoming accepted runtime evidence.

## Agent diagnostics

The worker response contains stable diagnostics with:

```text
code
stage
message
severity
details
```

Stable exit classes:

| Exit | Meaning |
|---:|---|
| 0 | worker completed successfully |
| 20 | invalid request/protocol/input |
| 30 | SOLIDWORKS/COM startup/version failure |
| 40 | CAD transfer/rebuild/read-back failure |
| 50 | artifact write/evidence failure |
| 70 | unexpected internal failure |

Host preflight uses `10` when required readiness is not READY.

## Runtime evidence-input producer

`run_solidworks_host_validation.py` is deliberately a producer, not the Primary runtime-evidence authority.

It:

1. loads and independently recomputes `mrea.cad-host-readiness.v1`;
2. requires the full minimum readiness check set;
3. builds the existing `mrea.solidworks-agent.v1` request from the canonical golden SketchPackage;
4. invokes the worker and records raw response + process exit;
5. rejects process/response exit disagreement;
6. requires successful response to include `real_host_executed=true` and actual `solidworks_version`;
7. feeds worker read-back through the existing canonical Chat 4 verification pipeline without rerunning SOLIDWORKS;
8. writes canonical `cad_package.json` and `cad_verification.json`;
9. independently reopens the native `.SLDPRT` and recomputes SHA-256;
10. writes `solidworks_runtime_inputs.json`.

The side-local input-bundle schema is:

```text
mrea.solidworks-runtime-inputs.v1
```

It contains:

- full host-readiness payload;
- agent process exit;
- `real_host_executed`;
- actual SOLIDWORKS version;
- `sketch_package_id`;
- bindings/vendor refs;
- normalized read-back dimensions;
- constraint conflicts;
- artifacts + SHA-256;
- diagnostics;
- canonical verification report.

It intentionally has no final runtime `status` field. Primary Chat 4 must consume these facts and apply its own `mrea.cad-runtime-evidence.v1` rules.

## One-command controlled-host procedure

```powershell
cd chat_4_cad_bridge_verification

.\scripts\run_solidworks_pass3_host_validation.ps1 `
  -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS" `
  -OutputDir ".\artifacts\solidworks-pass3"
```

Optional explicit template:

```powershell
-PartTemplate "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\Part.prtdot"
```

The wrapper performs:

```text
prebuild readiness (when agent missing)
build agent when needed
final fail-closed readiness
controlled worker transfer
canonical numerical verification
native artifact hash re-check
evidence-input emission
```

A successful Side Chat 4B run prints:

```text
CANONICAL_CAD_VERIFICATION=VERIFIED
SIDE_HOST_EVIDENCE=READY_FOR_PRIMARY_EVALUATION
FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4
```

It does not print `REAL_HOST_RESULT=VERIFIED`.

## Output files

On a successful controlled host run the output directory contains at least:

```text
host_readiness.json
solidworks_agent_response.json
solidworks_runtime_inputs.json
cad_package.json
cad_verification.json
<SketchPackage id>.SLDPRT
```

A prebuild readiness file may also be present when the worker had to be built.

## Real-host truth

No actual Windows 11 + SOLIDWORKS 2026 host is available in the ChatGPT execution environment used for this correction. Therefore:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

Neither is promoted from static checks, canonical tests, or source inspection.
