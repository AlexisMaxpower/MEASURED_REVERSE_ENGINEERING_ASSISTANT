# ORCHESTRATOR DIRECTIVE — Chat 3

**Revision:** `OD-2026-10-01-005`  
**Control owner:** central orchestration  
**Issued as:** Round-12 final control-plane repair by Orchestrator 2  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes `OD-2026-09-30-004` and every historical instruction that pins Chat 3 to `chat-3/pass-8`, Round-4 replay, or old shared-test drift.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch the new worker pass from the then-current shared `main`;
4. do not reuse a historical Chat-3 pass branch as the implementation base.

Round 12 integrates the explicit `UncertaintyAwareGeometryConflictDetector` policy and its regression tests. The policy remains opt-in; the established default detector is unchanged.

## Slice ownership

Chat 3 owns Geometry & Semi-Automatic Sketch: coordinate normalization, geometry extraction/graph, measurement binding, conflict visibility, constraint candidates/residual/confidence behavior and canonical SketchPackage production.

Preserve these invariants:

- physical measurements remain stronger evidence than inferred geometry;
- geometry never silently changes verified physical values/provenance;
- normalization remains in Chat 3 rather than Chat 2;
- ambiguous/unsupported geometry and constraints fail closed or remain explicit unresolved state;
- uncertainty may affect comparison policy but may not fabricate/strengthen upstream evidence;
- CAD-vendor behavior remains outside Chat 3;
- canonical contracts/shared CI are not changed without an approved central change.

## Next pass rule

This control document intentionally does not invent the next feature. Execute the active worker-round/user task for Chat 3 after resolving the current certified `main`. If no current task exists, stop rather than reviving an old OD-004 task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-3 plus Chat2->Chat3/Chat3->Chat4 and contract gates as applicable, publish a truthful handoff with exact SHA/CI evidence, and do not merge directly to `main`.
