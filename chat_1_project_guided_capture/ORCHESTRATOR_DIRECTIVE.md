# ORCHESTRATOR DIRECTIVE — Chat 1

**Revision:** `OD-2026-10-02-010`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-1 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_17_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-17 closure state;
4. do not use a historical pass or integration branch as the implementation base.

## Slice ownership

Chat 1 owns Project & Guided Capture. Preserve explicit recapture lineage, immutable clean-reference truth, attributable provenance and canonical-contract ownership. Voice triggers are capture-control provenance only and must not create metrology truth. Prepared-clean-reference readiness remains operator/setup guidance: any required unknown/failed preparation check must block capture mutation rather than being promoted into measurement truth.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-1 handoffs.

## Next pass rule

Execute the active worker-round/user task for Chat 1. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-1 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
