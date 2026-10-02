# MREA Orchestration State

**Control owner:** central orchestration  
**Directive revision:** `OD-2026-10-02-010`  
**Status:** `ROUND_17_CLOSED_GREEN_SOFTWARE`

## Round 17 authority

```text
ROUND_17_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

Round 17 is the accepted repository baseline. Final Orchestrator 3 independently audited actual GitHub refs, worker provenance, candidate source, canonical boundaries, critical fail-closed paths and exact-head Actions evidence before authorizing merge.

Accepted Round-17 candidate:

```text
86809d59f4f54f91c18da6e29bae02580cc3d56d
```

Audited integration merge to `main`:

```text
d3477c0f0451abdc52726e810d1099fff54e4482
```

That exact merge SHA passed the complete ordinary and truth post-merge software suites before this closure state was issued.

Historical Pass-17 worker branches, integration candidate and Orchestrator-1/2 audit records remain audit history only. They are not implementation baselines for a new pass.

## Round 17 integrated scope

- Chat 1 — fail-closed prepared-clean-reference capture gate; setup/operator readiness remains separate from physical measurement truth and blocked preparation cannot mutate capture state.
- Chat 2 — durable hands-free restart recovery for exact-context unverified candidates; ambiguous, verified or mismatched recovery fails closed and confirmation remains explicit-user-only.
- Chat 3 — verified angular local-DOF diagnosis with explicit shared-vertex topology witness, uncertainty-bounded compatibility and fail-closed unsupported/ambiguous geometry.
- Chat 4 — normalized canonical `ArtifactReference` boundary with required/optional field/type checks, duplicate-ID rejection and unknown-field rejection; Chat 4b adds fail-closed SOLIDWORKS rebuild checks before accepting relation creation or native save/read-back.
- Chat 5 — GET-only revision-change explanation HTTP surface over durable comparison facts and exact evidence identifiers, without ranking, recommendation, causality or unsupported engineering inference.

One historical Orchestrator-1 audit phrase described `byte_size` handling for Chat 4. That phrase is non-authoritative and inaccurate: canonical `ArtifactReference` v1 has no `byte_size` field. The accepted implementation matches the actual canonical field set and rejects unknown top-level fields.

## Standing SOLIDWORKS host qualification

Real-host qualification remains a standing environment qualification, not a round-level software result.

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

Round 17 changed fingerprinted host-boundary code, including `SolidWorksTransfer.cs`. A prior positive qualification applies only when its recorded source/boundary fingerprint matches the current repository boundary and the controlled host has not materially changed. Linux/software CI, mocks and static checks are not positive real-host evidence.

## Worker-start authority

Every new full worker pass must:

1. read this file and require `ROUND_17_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
2. start from the then-current shared `main` containing this Round-17 closure state;
3. use a new pass branch rather than any historical Pass-17 worker or integration branch;
4. preserve slice ownership, provenance, explicit-confirmation requirements and fail-closed truth boundaries;
5. follow the active worker-round/user task rather than reviving an historical task;
6. treat SOLIDWORKS host qualification as out-of-band unless the active task explicitly changes or validates its fingerprinted host boundary.
