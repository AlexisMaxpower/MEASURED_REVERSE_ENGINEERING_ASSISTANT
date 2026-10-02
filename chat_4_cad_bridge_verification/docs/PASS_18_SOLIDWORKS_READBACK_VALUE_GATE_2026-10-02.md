# Pass 18 — SOLIDWORKS Read-back Value Gate

**Role:** Chat 4B — SOLIDWORKS vendor implementation  
**Baseline:** `main@af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`  
**Directive:** `OD-2026-10-02-010`

## Problem

The real-host worker calls `IDimension.GetSystemValue3(...)` and then converts the returned `object` into a numerical read-back value.

Before Pass 18 the helper `FirstDouble(...)` accepted a direct `double`, otherwise attempted to read the first array item, and finally fell back to `Convert.ToDouble(raw, ...)`.

That fallback was too permissive for verification evidence. A missing, empty, unexpected or non-finite SOLIDWORKS payload must not be normalized into a plausible canonical number.

## SOLIDWORKS API basis

SOLIDWORKS API documents `IDimension.GetSystemValue3` as returning `System.Object` containing the dimension value in system units. The worker calls it with `swThisConfiguration`, so the accepted vendor-side shapes are deliberately narrow:

- one direct `double`; or
- an array containing exactly one `double`.

Reference:

`https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IDimension~GetSystemValue3.html`

## Change

`SolidWorksTransfer.cs` now routes every real dimension read-back through `RequireFiniteSystemValue(raw, dimension_id)` before unit normalization.

The gate rejects:

- `null` payloads;
- non-array/non-double payloads;
- arrays with zero or more than one item for the `swThisConfiguration` call;
- array items that are not `double`;
- `NaN` or infinite values.

All rejected cases throw `InvalidOperationException`, which remains in the existing CAD-transfer failure path (`exit_code = 40`). No read-back item or successful worker response is emitted from that execution.

## Truth boundary

This pass does not change canonical contracts, tolerances, verification policy or Primary Chat-4 response normalization. It only prevents malformed SOLIDWORKS runtime values from becoming vendor read-back evidence.

It does not claim that a real SOLIDWORKS 2026 host was executed. Because `SolidWorksTransfer.cs` is part of the fingerprinted host boundary, standing host qualification evidence must match the new source fingerprint before it can qualify this boundary.

## Verification

Added `tests/test_solidworks_readback_value_gate.py` to assert:

- every current `GetSystemValue3` result is routed through the new gate;
- the permissive `FirstDouble` path is removed;
- missing, ambiguous, non-numeric and non-finite payloads are explicitly rejected in source;
- exceptions from this path remain classified as CAD transfer failures by `Program.cs`.
