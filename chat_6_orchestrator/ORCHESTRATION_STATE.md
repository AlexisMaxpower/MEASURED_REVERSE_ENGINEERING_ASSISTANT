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

are retired as round-level status fields. They are one standing environment qualification named:

```text
SOLIDWORKS_HOST_QUALIFICATION
```

Source of truth:

- `.github/workflows/solidworks_host_qualification.yml`
- `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`
- the latest successful workflow artifact `solidworks_host_qualification.json`

Current migration state:

```text
SOLIDWORKS_HOST_QUALIFICATION = NOT_YET_EXECUTED_ON_REGISTERED_HOST
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

A successful qualification closes all three legacy sub-gates in one run by proving a fresh production C# build against the installed SOLIDWORKS 2026 interops, real COM execution, native `.SLDPRT` generation and real dimension read-back.

Once successful, the qualification is reusable across later software rounds while its recorded host-boundary fingerprint is unchanged. Unrelated slice changes do not invalidate it.

Future workers and orchestrators must not copy the three old `UNVERIFIED` lines into ordinary handoffs or round verdicts. Mention the standing qualification only when its state changes, its fingerprint becomes stale, or the round explicitly concerns real-host SOLIDWORKS behavior.

## Worker-start authority

Every new worker pass must:

1. start from the then-current shared `main`;
2. use a new pass branch rather than an historical branch as implementation base;
3. preserve slice ownership, provenance and fail-closed truth boundaries;
4. follow the active worker-round/user task rather than reviving an old directive;
5. treat SOLIDWORKS host qualification as out-of-band unless the task changes its fingerprinted host boundary.
