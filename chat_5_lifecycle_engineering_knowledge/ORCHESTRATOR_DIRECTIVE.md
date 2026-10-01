# ORCHESTRATOR DIRECTIVE — Chat 5

**Revision:** `OD-2026-10-02-009`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-5 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_16_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-16 closure state;
4. do not use a historical pass or integration branch as the implementation base.

## Slice ownership

Chat 5 owns Lifecycle & Engineering Knowledge. Preserve manufacturing-eligibility truth, deterministic lifecycle transitions, snapshot/cursor semantics and the rule that lifecycle/knowledge code cannot promote unverified CAD/runtime facts. Durable comparisons and explanations must stay bound to committed snapshot facts and exact source records/artifacts; they must not introduce ranking, recommendation, causality or unsupported engineering inference.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-5 handoffs.

## Next pass rule

Execute the active worker-round/user task for Chat 5. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-5 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
