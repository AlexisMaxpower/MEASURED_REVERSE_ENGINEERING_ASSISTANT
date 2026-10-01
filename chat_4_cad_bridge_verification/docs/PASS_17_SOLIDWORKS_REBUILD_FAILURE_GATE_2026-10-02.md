# Pass 17 — SOLIDWORKS Rebuild Failure Gate

**Owner:** Chat 4B — SOLIDWORKS Vendor Implementation  
**Date:** 2026-10-02  
**Baseline:** `main@933d925c69944d40859ae1f9ff80d7a3ecb7f760`  
**Directive:** `OD-2026-10-02-009`

## Problem

`SolidWorksTransfer` called `IModelDoc2.EditRebuild3()` after relation creation and before native save/read-back but ignored its Boolean result.

SOLIDWORKS API documents `EditRebuild3()` as returning `true` when the required rebuild succeeds and `false` otherwise. Ignoring `false` allowed a failed rebuild to continue toward relation-count inspection, native `.SLDPRT` save and dimension read-back.

Official API reference:

`https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelDoc2~EditRebuild3.html`

## Change

A vendor-local `RequireSuccessfulRebuild(...)` helper now owns every `EditRebuild3()` call in `SolidWorksTransfer`.

It is used:

1. immediately after each canonical relation is added, before relation-count/over-definition acceptance;
2. after leaving the sketch and before native save/read-back.

A `false` rebuild result throws `InvalidOperationException` with stage context. The existing worker error boundary classifies that as `CAD_TRANSFER_FAILED` / exit `40`.

## Truth boundary

This change does not infer successful real-host execution. It only closes a deterministic source-level false-success path.

No canonical contracts, tolerances, verification policy, shared CI, Primary Python adapter code or adjacent chat code are changed.

Because `SolidWorksTransfer.cs` is part of the fingerprinted host boundary, this source change changes the boundary fingerprint. Any previously positive `SOLIDWORKS_HOST_QUALIFICATION` is reusable only if its recorded fingerprint matches the resulting repository boundary, per standing policy.

## Regression coverage

`tests/test_solidworks_rebuild_failure_gate.py` checks that:

- transfer call sites use the checked rebuild helper;
- only the helper invokes `EditRebuild3()`;
- `false` rebuild fails closed;
- the exception remains inside the existing CAD-transfer failure class rather than artifact/success handling.

Final acceptance remains repository exact-head CI plus the standing controlled-host qualification when real SOLIDWORKS behavior is required.
