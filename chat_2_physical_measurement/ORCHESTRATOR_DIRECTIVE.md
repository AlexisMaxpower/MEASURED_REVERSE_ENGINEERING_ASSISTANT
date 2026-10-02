# ORCHESTRATOR DIRECTIVE — Chat 2

**Revision:** `OD-2026-10-02-010`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-2 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_17_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-17 closure state;
4. do not use a historical pass/readiness/integration branch as the implementation base.

## Slice ownership

Chat 2 owns Physical Measurement. Preserve measurement provenance, explicit user confirmation, uncertainty truth, raw anchors and the rule that downstream AI/geometry/CAD cannot silently rewrite verified physical facts. Durable session storage and enumeration must remain fail-closed. Hands-free restart recovery may resume only a matching durable unverified candidate; ambiguous, verified or context-mismatched recovery must not invent an actionable state. Confirmation remains explicit-user-only.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-2 handoffs.

## Next pass rule

Execute the active worker-round/user task for Chat 2. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-2 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
