# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-10-01-005`  
**Control owner:** central orchestration  
**Issued as:** Round-12 final control-plane repair by Orchestrator 2  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes `OD-2026-09-30-004` and every historical instruction that pins Chat 4 to `chat-4/pass-7` or forbids work beyond the old Round-4 cut.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch the new worker pass from the then-current shared `main`;
4. do not reuse a historical Chat-4/4B pass branch as the implementation base.

Round 12 integrates the broader declared Python -> C# SOLIDWORKS worker capability fingerprint in addition to the existing constraint fingerprint. Its documented scope is declared-capability compatibility plus selected source-parity checks, not proof of complete behavioral equivalence.

## Slice ownership

Chat 4 owns CAD Bridge & Verification, including generic CAD transfer/verification and SOLIDWORKS-specific behavior behind the vendor/process boundary.

Preserve these invariants:

- canonical verification remains vendor-neutral;
- unsupported vendor cases fail closed;
- vendor/process success alone does not promote canonical verification;
- real-host execution is not inferred from Linux CI, static checks, mocks or test doubles;
- capability/protocol compatibility checks occur before CAD mutation where designed;
- canonical contracts/shared CI are not changed without an approved central change.

## External truth

Until actual controlled-host evidence exists:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Next pass rule

This control document intentionally does not invent the next feature. Execute the active worker-round/user task for Chat 4 after resolving the current certified `main`. If no current task exists, stop rather than reviving an old OD-004 task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-4 generic plus adjacent boundary/contract gates, preserve external-host truth, publish a truthful handoff with exact SHA/CI evidence, and do not merge directly to `main`.
