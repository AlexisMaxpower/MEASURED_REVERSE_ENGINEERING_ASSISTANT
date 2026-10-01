# Chat 4B — Pass 16 Driven-Dimension Conflict Evidence

**Date:** 2026-10-02
**Branch:** `chat-4b/pass-16`
**Role:** SOLIDWORKS 2026 vendor implementation / real-host boundary
**Base:** shared `main@99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Purpose

The SOLIDWORKS worker previously treated every non-success return from `IDimension::SetSystemValue3(...)` as the same hard transfer failure. SOLIDWORKS exposes one materially different status: `swSetValue_DrivenDimension`, meaning the dimension cannot be set because it is driven by geometry.

That status is dimension-specific solver evidence and can be preserved without rewriting the requested measured value. The worker already returns `read_back.constraint_conflicts` as dimension IDs, and the canonical verification path already understands a conflict as distinct from an ordinary numerical mismatch.

## Implemented vendor behavior

For each created verified dimension:

1. call `SetSystemValue3(...)` exactly as before;
2. when the result is `swSetValue_DrivenDimension`, append that canonical `dimension_id` to the worker-local conflict list and continue;
3. keep the dimension binding so traceability is preserved;
4. rebuild/save/read the actual SOLIDWORKS dimension value exactly as before;
5. emit the collected IDs in `read_back.constraint_conflicts`;
6. keep every other non-success `SetSystemValue3` status as a hard `InvalidOperationException`.

No requested measurement is corrected or silently replaced.

## Deliberate scope boundary

This pass does **not** reinterpret arbitrary SOLIDWORKS failures as constraint conflicts.

In particular:

- relation creation failure remains a hard worker failure;
- `swOverDefining` relation detection remains a hard worker failure because the current vendor layer cannot deterministically map that sketch-level condition to a specific canonical dimension ID;
- invalid values, unloaded models, frozen owners and unknown set-value failures remain hard failures;
- no claim is made that SOLIDWORKS reports every solver conflict through `swSetValue_DrivenDimension`;
- no real-host success is inferred from source/static tests.

## Verification

A vendor-specific source test proves that:

- driven-dimension handling is checked before generic set-value failure handling;
- the exact `dimension_id` is preserved as conflict evidence;
- the response emits the collected conflict list;
- generic non-driven failures remain fail-closed;
- relation over-definition is not silently reclassified.

`SolidWorksTransfer.cs` is part of the standing host-boundary fingerprint, so this pass changes that fingerprint. Any previous positive `SOLIDWORKS_HOST_QUALIFICATION` is reusable only if its recorded fingerprint matches the new boundary and the controlled host has not materially changed.

Real Windows 11 x64 + SOLIDWORKS 2026 execution remains governed only by the standing `SOLIDWORKS_HOST_QUALIFICATION` workflow.
