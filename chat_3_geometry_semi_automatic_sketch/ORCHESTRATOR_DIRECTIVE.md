# ORCHESTRATOR DIRECTIVE — Chat 3

**Revision:** `OD-2026-10-02-011`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-3 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_18_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-18 closure state;
4. do not use a historical Pass-18 worker or integration branch as the implementation base.

## Slice ownership

Chat 3 owns Geometry & Semi-Automatic Sketch. Preserve physical-measurement priority, explicit unresolved geometry, fail-closed constraint behavior and the rule that geometry cannot silently rewrite verified upstream truth. Local freedom/DOF analysis, including arc contact/tangency and angular relations, is diagnostic only: unsupported semantics, conflicts, unresolved bindings, invalid units or ambiguous topology must fail closed rather than inventing equations, topology witnesses, confidence or tolerance. Explicit geometric/topology witnesses remain mandatory where the implemented relation semantics require them.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-3 handoffs.

## Next pass rule

Execute the active worker-round/user task for Chat 3. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-3 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
