# Chat 4 — Pass 18 SOLIDWORKS Native Artifact Request Identity

**Date:** 2026-10-02  
**Branch:** `chat-4/pass-18`  
**Base:** shared `main@af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`

## Purpose

Round 16 made an `OK` SOLIDWORKS worker response complete with respect to requested verified dimensions and required one native `SOLIDWORKS_PART` artifact. Round 17 normalized every returned artifact against canonical `ArtifactReference` v1 shape.

One request-correlation gap remained: a structurally valid native part artifact could still carry an `artifact_id` produced for a different `SketchPackage` while the dimension IDs happened to match the current request.

The production C# worker already deterministically emits:

```text
SWPART-{sketch_package_id}
```

for its native part artifact. Pass 18 makes that existing worker identity convention part of the Python SOLIDWORKS success boundary.

## Implemented

After the existing success-response completeness checks, `SolidWorksAgentAdapter` now requires the single native `SOLIDWORKS_PART` artifact to have exactly:

```text
artifact_id == "SWPART-" + request.sketch_package_id
```

A stale or cross-request `OK` response with otherwise valid bindings, read-back values and canonical artifact shape therefore fails closed with `CadAdapterError` before the vendor result can enter canonical CAD verification.

No artifact is rewritten, renamed or silently rebound to the active request.

## Verification

`tests/test_solidworks_native_artifact_request_identity.py` covers both directions:

- the native artifact identity generated for the current request is accepted;
- a structurally valid native artifact carrying another request's `SketchPackage` identity is rejected.

The test intentionally keeps dimension IDs and numerical read-back valid in the negative case so the failure proves request identity correlation rather than another completeness guard.

## Scope boundary

This pass changes only Chat-4-owned SOLIDWORKS adapter-boundary software, tests and documentation.

It does not change:

- canonical shared schemas or fixtures;
- canonical verification semantics;
- worker mutation or SOLIDWORKS geometry behavior;
- shared CI;
- artifact naming in the C# worker, which already used the required deterministic identity.

`solidworks_agent.py` participates in the standing SOLIDWORKS host-boundary fingerprint. Any reusable positive `SOLIDWORKS_HOST_QUALIFICATION` evidence must therefore match the resulting current fingerprint. This software pass does not claim a real-host execution.
