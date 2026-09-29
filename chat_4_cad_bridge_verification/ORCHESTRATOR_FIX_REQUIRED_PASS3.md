# ORCHESTRATOR FIX REQUIRED — Side Chat 4B Pass 3

**Owner:** Chat 6 — Primary Orchestrator  
**Status:** `FIX_REQUIRED`  
**Branch:** `chat-4b/pass-3`

## Upload audit result

The branch exists remotely and is not missing from GitHub. Current remote head before this directive was `18ec8d74650b634cfa13bb4e50e0e0b89308ba6e`.

However, the expected Pass-3 implementation result is not present. The branch contains only task/setup material. The required file `chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md` is absent.

This is therefore **not an upload retry problem**: there is no completed side implementation commit currently available in the remote repository to re-upload.

## Required work

Implement the Side Chat 4B assignment from `docs/SIDE_CHAT_4B_PASS_3_TASK.md`:

- Windows/x64 host-readiness probes;
- .NET/agent prerequisite diagnostics;
- SOLIDWORKS availability/version diagnostics where feasible;
- interop availability diagnostics;
- writable artifact/output diagnostics;
- deterministic machine-readable failure reasons and exit codes;
- native artifact/runtime evidence integration expected by Primary Chat 4;
- preserve fail-closed behavior;
- do not claim real SOLIDWORKS runtime success without a real host execution.

Then publish:

`chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md`

The handoff must include final SHA, all changed files, tests/builds actually executed, exit-code behavior, C# compilation status, real-host status and limitations.

After publishing the handoff, freeze this branch and return control to Primary Chat 4 / Chat 6.
