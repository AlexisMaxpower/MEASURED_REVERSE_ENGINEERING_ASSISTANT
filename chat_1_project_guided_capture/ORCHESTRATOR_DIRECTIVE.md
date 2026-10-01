# ORCHESTRATOR DIRECTIVE — Chat 1

**Revision:** `OD-2026-10-01-005`  
**Control owner:** central orchestration  
**Issued as:** Round-12 final control-plane repair by Orchestrator 2  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes `OD-2026-09-30-004` and every historical instruction that pins Chat 1 to `chat-1/pass-4` or a Round-4 Stage-1 state.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch the new worker pass from the then-current shared `main`;
4. do not reuse a historical Chat-1 pass branch as the implementation base.

Round 12 contains no new Chat-1 product delta. The current integrated Chat-1 surface on `main` remains authoritative.

## Slice ownership

Chat 1 owns Project & Guided Capture: project/session capture flow, clean-reference lineage, capture quality/readiness, calibration/rectification capture-side state, and canonical CapturePackage production within the existing shared contract.

Preserve these invariants:

- recapture/replacement is explicit lineage, never silent mutation;
- provenance remains attributable to the correct capture generation;
- verified downstream physical facts are not rewritten by recapture;
- measurement, geometry, CAD and lifecycle ownership stays outside Chat 1;
- canonical contracts/shared CI are not changed without an approved central change.

## Next pass rule

This control document intentionally does not invent the next feature. Execute the active worker-round/user task for Chat 1 after resolving the current certified `main`. If no current task exists, stop rather than reviving an old OD-004 task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-1 plus adjacent boundary/contract gates, publish a truthful handoff with exact SHA/CI evidence, and do not merge directly to `main`.
