# MREA Orchestration State

**Control owner:** central orchestration  
**Directive revision:** `OD-2026-10-02-011`  
**Status:** `ROUND_18_CLOSED_GREEN_SOFTWARE`

## Round 18 authority

```text
ROUND_18_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

Round 18 is the accepted repository baseline. Final Orchestrator 3 independently audited actual GitHub refs, worker provenance, candidate source, canonical/truth boundaries, critical fail-closed behavior and exact-head Actions evidence. Previous orchestrator prose was treated as a claim to verify rather than authority.

Accepted final Round-18 candidate:

```text
01bfa765a7c651f480636ec7ad86ef0bd12e1764
```

Audited integration merge to `main`:

```text
80c1a1fc22c0ec33bc0529e62d2d39722f4a422a
```

That exact merge SHA passed the complete ordinary and truth post-merge software suites before this closure state was issued.

Historical Pass-18 worker branches, the integration candidate and Orchestrator-1/2 audit records remain audit history only. They are not implementation baselines for a new pass.

## Round 18 integrated scope

- Chat 1 — preparation-aware guided capture remains fail closed; setup readiness cannot create metrology truth and blocked preparation cannot silently advance capture state.
- Chat 2 — explicit manual anchor selection/snap decisions preserve manual-versus-vision provenance and require explicit user confirmation before a proposed snap is accepted.
- Chat 3 — local freedom diagnostics add arc/contact/tangent and angular topology handling with explicit witnesses; ambiguous or unsupported topology remains indeterminate rather than invented.
- Chat 4 — SOLIDWORKS native artifact success is request-correlated through the canonical artifact identity; stale/cross-request artifact evidence fails closed.
- Chat 4b — SOLIDWORKS transfer/read-back hardening rejects failed rebuilds and non-finite/unexpected system-value shapes before positive transfer evidence.
- Chat 5 — durable physical field status is projected only from a validated physical timeline. Orchestrator 2 repaired historical-event vocabulary validation; Final Orchestrator 3 additionally repaired missing state-machine transition replay, TESTED outcome validation and activation-after-PASSED enforcement.

## Final Orchestrator 3 repair

The O2 candidate `ef37c445c67642a9274e477a95734102c7abed34` still accepted durable histories made only from known event names even when the sequence could not have been produced by the authoritative physical lifecycle state machine, for example `MANUFACTURED -> ACTIVATED`. Such corruption could be projected as a plausible current state.

Final Orchestrator 3 repaired this fail-closed gap on the integration candidate in:

```text
08abe2afccaad30f63f4c47b55a5db4a954d3985
e76a8a393c49b98455295d34f222976385e41000
01bfa765a7c651f480636ec7ad86ef0bd12e1764
```

The repaired projection requires `MANUFACTURED` first, replays only legal physical transitions, requires an explicit `PASSED`/`FAILED` outcome for every `TESTED` event, and permits `ACTIVATED` only immediately after a persisted `TESTED/PASSED` event. Regression coverage includes impossible known-vocabulary histories and a legal full lifecycle path.

## Standing SOLIDWORKS host qualification

Real-host qualification remains a standing environment qualification, not a round-level software result.

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

Round 18 changed fingerprinted host-boundary source including `solidworks_agent.py` and `SolidWorksTransfer.cs`. A prior positive qualification applies only when its recorded source/boundary fingerprint matches the current repository boundary and the controlled host has not materially changed. Linux/software CI, mocks and static checks are not positive real-host evidence.

## Worker-start authority

Every new full worker pass must:

1. read this file and require `ROUND_18_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
2. start from the then-current shared `main` containing this Round-18 closure state;
3. use a new pass branch rather than any historical Pass-18 worker or integration branch;
4. preserve slice ownership, provenance, explicit-confirmation requirements and fail-closed truth boundaries;
5. follow the active worker-round/user task rather than reviving an historical task;
6. treat SOLIDWORKS host qualification as out-of-band unless the active task explicitly changes or validates its fingerprinted host boundary.
