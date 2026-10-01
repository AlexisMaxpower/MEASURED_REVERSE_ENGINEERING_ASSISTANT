# MREA Orchestration State

**Control owner:** central orchestration  
**Directive revision:** `OD-2026-10-01-008`  
**Status:** `ROUND_14_CLOSED_GREEN_SOFTWARE`

## Round 14 authority

```text
ROUND_14_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

Round-14 integration is the accepted repository baseline. The audited integration merge is `94ea4e957ec85d9276303d30124910497e2ddafa`; the final closure/control commit containing this state is the required starting baseline for the next worker pass.

Historical worker branches, integration candidates and older round certification records remain audit history only. They are not implementation baselines for a new pass.

## Round 14 integrated scope

- Chat 1 — quality/lifecycle synchronization around the active immutable clean-reference attempt; rejected quality cannot be accepted without a new passing attempt.
- Chat 2 — deterministic durable measurement-session enumeration with optional project scoping and fail-closed stored-session decoding.
- Chat 3 — uncertainty-aware verified-measurement contradiction policy for the supported EQUAL/CONCENTRIC cases without rewriting measured truth.
- Chat 4 — fail-closed SOLIDWORKS entity-geometry capability rules included in the Python/C# worker capability handshake before COM startup.
- Chat 5 — durable snapshot-bound revision comparison plus GET-only read exposure through the existing guarded lifecycle knowledge surface.

Shared Round-14 integration hardening also generalized Truth CI from the historical single integration branch to versioned `integration/pass-*-candidate` branches and added regression coverage for that trigger and the SOLIDWORKS host-boundary fingerprint surface.

Final Orchestrator 2 independently audited actual source, replay identity, integration behavior and exact-head CI before merging the candidate. The exact merge SHA then passed the complete ordinary and truth post-merge suites before this closure state was issued.

## Standing SOLIDWORKS host qualification

The former per-round carry-forward fields remain retired. Real-host qualification is one standing environment qualification named `SOLIDWORKS_HOST_QUALIFICATION`.

Operational authority is dynamic rather than copied into this file:

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

Round 14 changed fingerprinted SOLIDWORKS host-boundary code by adding entity-geometry capability rules to the worker compatibility surface. Any previous positive qualification is reusable only when its recorded host-boundary fingerprint still matches the current repository boundary and the controlled host has not materially changed. No Linux/software CI result is promoted to positive real-host qualification.

When real-host status is relevant, resolve it directly from the dedicated workflow and its generated `solidworks_host_qualification.json`. Do not manually mirror that dynamic result into ordinary round state, worker handoffs, README files or implementation-state documents.

## Worker-start authority

Every new full worker pass must:

1. read this file and require `ROUND_14_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
2. start from the then-current shared `main` containing this Round-14 closure state;
3. use a new pass branch rather than an historical branch as implementation base;
4. preserve slice ownership, provenance and fail-closed truth boundaries;
5. follow the active worker-round/user task rather than reviving an old task;
6. treat SOLIDWORKS host qualification as out-of-band unless the active task changes or explicitly validates its fingerprinted host boundary.
