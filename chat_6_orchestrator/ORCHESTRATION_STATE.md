# MREA Orchestration State

**Control owner:** central orchestration  
**Directive revision:** `OD-2026-10-01-006`  
**Status:** `ROUND_12_CLOSED_GREEN_SOFTWARE`

## Round 12 authority

```text
ROUND_12_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

Round-12 integration remains the accepted repository baseline. Historical Round-12 certification records remain audit history; this file is the current operational authority.

## Standing SOLIDWORKS host qualification

The former per-round carry-forward fields

`REAL_SOLIDWORKS_2026_HOST`, `PRODUCTION_CSHARP_INTEROP_BUILD`, and `NATIVE_SLDPRT_GENERATION_READBACK`

are retired as round-level status fields. They are three subchecks of one standing environment qualification named `SOLIDWORKS_HOST_QUALIFICATION`.

Operational authority is dynamic rather than copied into this file:

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

When real-host status is relevant, resolve it from the dedicated workflow and its generated `solidworks_host_qualification.json` evidence. Do not manually mirror that result into ordinary round state.

A successful qualification closes all three legacy sub-gates in one run by proving a fresh production C# build against the installed SOLIDWORKS 2026 interops, real COM execution, native `.SLDPRT` generation and real dimension read-back.

The qualification manifest records a host-boundary fingerprint. A successful qualification remains reusable across later software rounds while that fingerprint is unchanged and the controlled host has not materially changed. Unrelated slice changes do not invalidate it.

Future workers and orchestrators must not copy the three old `UNVERIFIED` lines into ordinary handoffs or round verdicts. Mention the standing qualification only when its state changes, its fingerprint becomes stale, the controlled host changes materially, or the round explicitly concerns real-host SOLIDWORKS behavior.

## Worker-start authority

Every new worker pass must:

1. start from the then-current shared `main`;
2. use a new pass branch rather than an historical branch as implementation base;
3. preserve slice ownership, provenance and fail-closed truth boundaries;
4. follow the active worker-round/user task rather than reviving an old directive;
5. treat SOLIDWORKS host qualification as out-of-band unless the task changes its fingerprinted host boundary.
