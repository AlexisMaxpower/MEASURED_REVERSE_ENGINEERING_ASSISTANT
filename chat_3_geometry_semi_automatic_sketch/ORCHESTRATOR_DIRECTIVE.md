# ORCHESTRATOR DIRECTIVE — Chat 3

**Revision:** `OD-2026-10-01-008`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-3 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_14_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-14 closure state;
4. do not use a historical pass branch as the implementation base.

## Slice ownership

Chat 3 owns Geometry & Semi-Automatic Sketch. Preserve physical-measurement priority, explicit unresolved geometry, fail-closed constraint behavior and the rule that geometry cannot silently rewrite verified upstream truth. Uncertainty-aware residual and contradiction policies remain measurement-grounded and must not invent confidence or tolerance from unsupported evidence.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-3 handoffs. Refer to `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md` only if the active task explicitly concerns that qualification.

## Next pass rule

Execute the active worker-round/user task for Chat 3. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-3 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
