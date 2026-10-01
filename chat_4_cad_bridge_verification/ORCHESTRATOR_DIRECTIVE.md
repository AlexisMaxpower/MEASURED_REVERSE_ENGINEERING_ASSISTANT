# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-10-01-006`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-4/4B directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. read `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`;
3. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
4. branch from the then-current shared `main`;
5. do not use a historical Chat-4/4B pass branch as the implementation base.

## Slice ownership

Chat 4 owns CAD Bridge & Verification, including generic CAD transfer/verification and SOLIDWORKS-specific behavior behind the vendor/process boundary.

Preserve these invariants:

- canonical verification remains vendor-neutral;
- unsupported vendor cases fail closed;
- vendor/process success alone does not promote canonical verification;
- real-host execution is never inferred from Linux CI, static checks, mocks or test doubles;
- capability/protocol compatibility checks occur before CAD mutation where designed;
- canonical contracts/shared CI are not changed without an approved central change.

## Standing SOLIDWORKS host qualification

The old three-line per-round carry-forward is retired. Do **not** emit these historical fields as ordinary Chat-4 handoff boilerplate:

- `REAL_SOLIDWORKS_2026_HOST`
- `PRODUCTION_CSHARP_INTEROP_BUILD`
- `NATIVE_SLDPRT_GENERATION_READBACK`

They are now subchecks of the single standing `SOLIDWORKS_HOST_QUALIFICATION` workflow.

Qualification is positive only after `.github/workflows/solidworks_host_qualification.yml` succeeds on a self-hosted Windows x64 runner labelled `solidworks-2026`. One successful run proves all three subchecks together and records a host-boundary fingerprint.

After a successful run, preserve that qualification across unrelated later rounds while the fingerprinted host boundary is unchanged. Re-run only when Chat 4 changes a fingerprinted SOLIDWORKS host-boundary file, the controlled host changes materially, or the previous qualification is invalidated.

Until the first real-host run, the standing qualification may be `NOT_YET_EXECUTED_ON_REGISTERED_HOST`, but that state is not a software-round blocker and must not turn otherwise-green ordinary rounds into `ACCEPTED_WITH_EXTERNAL_GATE`.

## Next pass rule

Execute the active worker-round/user task for Chat 4. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-4 generic plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`. Mention the standing host qualification only when its state/fingerprint is actually relevant to the pass.
