# CHANGE REQUEST 002 — SOLIDWORKS Adapter Environment Baseline

**From:** Chat 4 — CAD Bridge & Verification  
**To:** Chat 6 — Orchestrator / Repository Integrator  
**Status:** OPEN  
**Date:** 2026-09-29

## Problem

The generic CAD gate is now independent of vendor runtime:

```text
SketchPackage v1
→ normalized MappedSketchPackage
→ CadAdapter boundary
→ normalized CadReadBack
→ CADVerificationReport v1
```

A deterministic `TEST_DOUBLE` covers the canonical golden flow without SOLIDWORKS.

The next stage is the real SOLIDWORKS adapter. Repository-wide target environment is not currently published, so Chat 4 must not silently choose an interop/runtime baseline that later conflicts with integration or release requirements.

## Decision requested

Please publish or approve the canonical v1 SOLIDWORKS adapter environment:

1. target SOLIDWORKS major version or supported version range;
2. Windows target/version range;
3. process architecture (`x64` expected unless explicitly decided otherwise);
4. .NET target (`net8.0-windows`, .NET Framework, or another explicit target);
5. SOLIDWORKS interop reference strategy;
6. COM apartment/threading policy;
7. whether adapter runs in-process, separate worker process, or separate Windows service;
8. test host strategy for integration tests requiring installed SOLIDWORKS;
9. CI/release-gate behavior when a SOLIDWORKS host is unavailable;
10. artifact location/registration boundary for generated native CAD files.

## Chat 4 recommendation for decision criteria

The selected baseline should:

- keep SOLIDWORKS-specific code behind the existing `CadAdapter` semantics;
- normalize read-back to canonical `mm` / `deg` before verification;
- preserve `dimension_id`, nullable `measurement_id`, and vendor dimension reference;
- allow pure unit/contract tests without launching SOLIDWORKS;
- isolate COM lifecycle failures from canonical domain logic;
- support a dedicated Windows integration-test path for real API verification.

## Impact if unresolved

Chat 4 can continue pure adapter-boundary tests and documentation, but should not create a production C# project or pin interop packages/framework targets without this decision.

## Shared contract impact

None requested. `mrea.contracts.v1` remains unchanged.
