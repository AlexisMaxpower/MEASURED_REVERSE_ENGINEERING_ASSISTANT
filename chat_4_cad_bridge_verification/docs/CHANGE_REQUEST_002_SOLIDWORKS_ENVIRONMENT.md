# CHANGE REQUEST 002 — SOLIDWORKS Adapter Environment Baseline

**From:** Chat 4 — CAD Bridge & Verification  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Status:** RESOLVED  
**Date:** 2026-09-29  
**Resolved by:** `chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`

## Problem

The generic CAD gate is independent of vendor runtime:

```text
SketchPackage v1
→ normalized MappedSketchPackage
→ CadAdapter boundary
→ normalized CadReadBack
→ CADVerificationReport v1
```

The next stage requires a concrete SOLIDWORKS environment baseline.

## Decision

Chat 6 approved the following v1 baseline:

- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- C#;
- .NET Framework 4.8 for the first adapter implementation;
- x64 process;
- out-of-process user-session CAD Agent/worker behind existing `CadAdapter` semantics;
- dedicated STA COM execution context;
- official/local SOLIDWORKS 2026 API/interop references;
- do not commit proprietary SOLIDWORKS binaries;
- generic/unit/contract tests stay independent of SOLIDWORKS;
- real adapter verification requires an explicit Windows 11 + SOLIDWORKS 2026 host;
- if the host is unavailable, the real-host gate is `UNVERIFIED/SKIPPED`, never PASS;
- native CAD output is registered through the existing CADPackage/artifact boundary rather than a new storage subsystem.

The full rationale, acceptance slice and consequences are canonicalized in:

`chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`

## Shared contract impact

None. `mrea.contracts.v1` remains unchanged.

## Follow-up

Chat 4 must follow `ORCHESTRATOR_DIRECTIVE.md` revision `OD-2026-09-29-002` on branch `chat-4/pass-2`.
