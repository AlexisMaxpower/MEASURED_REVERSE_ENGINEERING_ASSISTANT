# SOLIDWORKS SIDE HANDOFF — Chat 4B → Primary Chat 4

**Pass:** 3 FIX_REQUIRED correction  
**Directive:** `OD-2026-09-29-003`  
**Fix source:** `ORCHESTRATOR_FIX_REQUIRED_PASS3.md`  
**Branch:** `chat-4b/pass-3`  
**Fix-required starting head:** `8b2c358de3b7d4360abbbbb5abf8ddc1a5de69b3`  
**Implementation SHA before this handoff commit:** `36a5dcd0c2637a1bae91556ce36fcb971a3c3f18`  
**Date:** 2026-09-29

## Status

`READY_FOR_PRIMARY_CHAT_4_INTEGRATION`

Side Chat 4B's missing Pass-3 implementation is now present remotely.

Real Windows 11 + SOLIDWORKS 2026 execution:

```text
UNVERIFIED
```

C# production compilation against official SOLIDWORKS 2026 interop:

```text
UNVERIFIED
```

No real-host or production-build success is inferred from source inspection or pure tests.

## FIX_REQUIRED items completed by Side Chat 4B

The side assignment from `docs/SIDE_CHAT_4B_PASS_3_TASK.md` is implemented:

- Windows 11 x64 host probing;
- x64 process probing;
- .NET Framework 4.8 probing;
- MSBuild/build readiness probing;
- CAD Agent executable readiness;
- `SldWorks.Application` COM registration probing;
- actual SOLIDWORKS `RevisionNumber()` probing and 2026 revision-major enforcement;
- official SOLIDWORKS interop assembly probing;
- writable artifact/output-directory probing;
- explicit/default part-template probing;
- machine-readable `mrea.cad-host-readiness.v1` output;
- stable process exit classes;
- stable worker diagnostics;
- actual SOLIDWORKS version in worker response;
- raw worker response preservation;
- canonical read-back verification reuse;
- native `.SLDPRT` SHA-256 re-check outside the worker;
- side-local evidence-input bundle for Primary Chat 4;
- deterministic one-command Windows host procedure;
- removal of the old false `REAL_HOST_RESULT=VERIFIED` numerical-only marker.

## Changed files

Relative to Side Chat 4B FIX_REQUIRED head `8b2c358de3b7d4360abbbbb5abf8ddc1a5de69b3`:

### Modified

```text
chat_4_cad_bridge_verification/scripts/build_solidworks_agent.ps1
chat_4_cad_bridge_verification/scripts/run_solidworks_golden.py
chat_4_cad_bridge_verification/solidworks_agent/Program.cs
chat_4_cad_bridge_verification/solidworks_agent/ProtocolModels.cs
chat_4_cad_bridge_verification/solidworks_agent/README.md
chat_4_cad_bridge_verification/solidworks_agent/SolidWorksSession.cs
```

### Added

```text
chat_4_cad_bridge_verification/scripts/test_solidworks_host_readiness.ps1
chat_4_cad_bridge_verification/scripts/run_solidworks_host_validation.py
chat_4_cad_bridge_verification/scripts/run_solidworks_pass3_host_validation.ps1
chat_4_cad_bridge_verification/tests/test_solidworks_runtime_inputs.py
chat_4_cad_bridge_verification/docs/SOLIDWORKS_HOST_READINESS_PASS_3.md
chat_4_cad_bridge_verification/docs/BUILD_REUSE_CHECK_SOLIDWORKS_HOST_READINESS_PASS3.md
chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md
```

## Ownership preserved

Side Chat 4B did not modify:

```text
chat_4_cad_bridge_verification/src/mrea_cad_bridge/runtime_evidence.py
chat_4_cad_bridge_verification/tests/test_runtime_evidence.py
core/contracts/
tests/fixtures/contracts/
.github/workflows/
tests/integration/
```

The Chat-6-owned Chat 3 -> Chat 4 CI defect described in the FIX_REQUIRED instruction was not worked around here.

## Host readiness

The PowerShell probe emits `mrea.cad-host-readiness.v1` and produces at least these required checks:

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

When build is necessary it also checks:

```text
MSBUILD_AVAILABLE
```

Semantics are fail-closed:

- any required `FAIL` -> `FAILED`;
- otherwise any required `UNVERIFIED` -> `UNVERIFIED`;
- all required checks `PASS` -> `READY`.

The Python evidence producer independently recomputes readiness, requires the complete minimum code set and rejects a producer-reported aggregate that disagrees with its checks.

## Stable exit classes

### Host wrapper / preflight

```text
0   producer completed successfully
10  host preflight/build prerequisites not ready
20  invalid request/input
30  SOLIDWORKS/COM startup/version failure
40  CAD transfer/rebuild/read-back/canonical verification failure
50  native artifact or runtime-evidence-input integrity failure
70  unexpected internal failure
```

### C# CAD Agent

```text
0   completed successfully
20  invalid request/protocol/input
30  SOLIDWORKS/COM startup/version failure
40  CAD transfer/rebuild/read-back failure
50  artifact write failure
70  unexpected internal failure
```

The agent response includes `exit_code`; the producer rejects process/response exit-code disagreement.

## Worker runtime facts

Successful `mrea.solidworks-agent.v1` responses now include:

```text
real_host_executed
solidworks_version
exit_code
bindings
read_back
artifacts
diagnostics
```

Failures include stable diagnostic fields:

```text
code
stage
message
severity
details
```

The protocol identifier remains `mrea.solidworks-agent.v1`; canonical contracts are unchanged.

## COM lifecycle

`SolidWorksSession.Open()` now cleans partial startup state if failure occurs before a session is returned:

- closes a partially created document when possible;
- releases document COM references;
- calls `ExitApp()` only for a SOLIDWORKS instance launched by the failed startup attempt;
- never terminates an already-running attached user instance;
- releases application COM references.

Successful sessions preserve the existing behavior of not terminating the user's SOLIDWORKS session on normal worker disposal.

## Evidence-input bundle

Side Chat 4B emits:

```text
mrea.solidworks-runtime-inputs.v1
```

This is deliberately **not** `mrea.cad-runtime-evidence.v1` and is not a canonical/shared contract.

It contains:

- full host-readiness payload;
- worker exit code;
- `real_host_executed`;
- actual SOLIDWORKS version;
- `sketch_package_id`;
- dimension bindings/vendor refs;
- normalized read-back dimensions;
- constraint conflicts;
- native artifact metadata and SHA-256;
- worker/producer diagnostics;
- canonical CAD verification report.

There is intentionally no final runtime `status` field. Primary Chat 4 owns the final `VERIFIED / FAILED / UNVERIFIED` decision through its Pass-3 runtime-evidence layer.

## Artifact integrity

The producer does not rely only on the SHA-256 text returned by the C# worker. It:

1. requires a `SOLIDWORKS_PART` artifact;
2. requires a `file://` URI;
3. opens the generated native file;
4. recomputes SHA-256 independently;
5. fails with exit `50` on missing file/hash mismatch.

## One-command controlled-host procedure

On the supported host:

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

Sequence:

```text
prebuild readiness when needed
-> build/locate agent
-> final readiness
-> worker transfer
-> canonical read-back verification
-> native artifact hash re-check
-> evidence-input bundle
```

A successful Side Chat 4B execution may print:

```text
CANONICAL_CAD_VERIFICATION=VERIFIED
SIDE_HOST_EVIDENCE=READY_FOR_PRIMARY_EVALUATION
FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4
```

It does not claim final runtime VERIFIED.

## Legacy golden runner correction

The previous `run_solidworks_golden.py` printed:

```text
REAL_HOST_RESULT=VERIFIED
```

from numerical verification alone. That marker has been removed.

It now reports only:

```text
CANONICAL_CAD_VERIFICATION=VERIFIED
FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4
```

This closes a false-positive runtime-truth path.

## Tests actually executed

In the available Linux ChatGPT execution environment, a staging mirror of the new pure producer/test logic was executed with:

```text
python -m py_compile \
  scripts/run_solidworks_host_validation.py \
  tests/test_solidworks_runtime_inputs.py
```

Result:

```text
PASS
```

Then:

```text
python -m unittest tests/test_solidworks_runtime_inputs.py -v
```

Result:

```text
Ran 5 tests
OK
```

Covered:

- producer-reported false READY is rejected;
- missing mandatory readiness code is rejected;
- side evidence bundle is not final runtime evidence and has no final `status`;
- native artifact SHA-256 is independently accepted when correct;
- native artifact SHA-256 mismatch fails closed.

## Not executable in this environment

The following were not executed because this environment has no Windows PowerShell host, .NET Framework/MSBuild compiler, official SOLIDWORKS 2026 interop assemblies or SOLIDWORKS COM installation:

```text
PowerShell host preflight execution
C# production compilation
SOLIDWORKS COM startup
native .SLDPRT generation
real read-back from installed SOLIDWORKS
one-command Windows host procedure
```

Therefore:

```text
C# BUILD = UNVERIFIED
REAL_HOST = UNVERIFIED
```

## Known limitations

1. This Pass-3 correction intentionally does not expand the real worker beyond the existing LINE/CIRCLE first slice; POINT/ARC/ANGLE/additional constraints remain outside the host-readiness fix scope.
2. `mrea.solidworks-runtime-inputs.v1` is side-local integration material, not a new shared contract.
3. Final runtime status cannot become VERIFIED until the controlled Windows 11 + SOLIDWORKS 2026 procedure actually runs and Primary Chat 4 consumes its evidence.
4. Side branch is based on its independently issued Pass-3 baseline and therefore should be reconciled file-by-file into the newer Primary `chat-4/pass-3` rather than merged blindly.

## Requested integration action — Primary Chat 4

Primary Chat 4 should now:

1. take the Side Chat 4B diff from `8b2c358de3b7d4360abbbbb5abf8ddc1a5de69b3` through this handoff head;
2. reconcile only the listed SOLIDWORKS/vendor files and side test/docs into current `chat-4/pass-3`;
3. preserve Primary-owned `runtime_evidence.py`, `test_runtime_evidence.py`, canonical contracts and Chat-6-owned CI;
4. map the supplied host-readiness/worker/runtime-input facts into the existing Primary runtime-evidence path without promoting the side-local input schema to a shared contract;
5. use the corrected current shared baseline containing the Chat-6 Chat3->Chat4 integration-test fix at `1a54ef40f84119d7482d971deb1e58749bf657b0` when running relevant boundaries;
6. run the full Chat 4 regression plus Chat 3 -> Chat 4 and Chat 4 -> Chat 5 boundaries;
7. keep actual SOLIDWORKS runtime `UNVERIFIED` unless a real supported-host run supplies evidence;
8. replace the stale Pass-2 `ORCHESTRATOR_HANDOFF.md` with a genuine final **Pass-3** handoff;
9. freeze `chat-4/pass-3` after that final handoff.

## Branch freeze

After the commit that adds this file, Side Chat 4B considers `chat-4b/pass-3` **frozen** and returns control to Primary Chat 4 / Chat 6 unless `FIX_REQUIRED` is issued again.
