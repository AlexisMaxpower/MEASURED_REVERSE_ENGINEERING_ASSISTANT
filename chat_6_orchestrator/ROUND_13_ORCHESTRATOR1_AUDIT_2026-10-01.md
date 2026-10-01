# Round 13 — Orchestrator 1 Audit

**Date:** 2026-10-01  
**Role:** Orchestrator 1 / first managerial audit  
**Frozen shared base:** `main` @ `1a9341263827242f4a0f086a8455e979ba3d7bb4`

## Audit method

This audit was performed from live GitHub repository state after the parallel worker slice. Worker chat answers were not treated as evidence. Branch ancestry, changed-file scope, implementation code, tests, current central control-plane documents and exact GitHub Actions runs are the authority.

All Round-13 worker branches were found to be based on historical `main` @ `4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`, while current shared `main` is five commits ahead. Therefore no worker branch is merged directly. Round 13 is rebuilt as a selective replay on the frozen current base.

## Frozen worker heads

```text
Chat 1  chat-1/pass-13  e590080d1e6c01a68f86ce2847aa99dfdc335121
Chat 2  chat-2/pass-13  474cecf4294d9a25da0702611a1e3dfd19d3ba3d
Chat 3  chat-3/pass-13  4c01fca1816e98eb19236e0cc2c1adf21918712c
Chat 4  chat-4/pass-13  3e8bd429b3d87aaeb1b027042483ceeb8b0ab4a1
Chat 5  chat-5/pass-13  2ea11745e365f0e454c08e2e8ca89c1aa76846e3
```

`chat-1/pass-13-readiness` and `chat-1/pass-13-control` contain no commits ahead of the worker baseline and are not replay targets.

## Worker-slice review

### Chat 1 — no product delta

The Pass-13 branch contains readiness/handoff documentation only. No Capture product code or tests changed, so no Chat-1 worker content is replayed.

### Chat 2 — accepted with selective replay

Accepted capability: durable offline-first `SqliteMeasurementSessionRepository` behind the existing repository boundary.

Reviewed properties:

- private versioned local persistence schema, not a shared contract;
- Decimal values serialized losslessly as strings;
- timezone-aware session/measurement timestamps preserved;
- 1..3 ordered anchors, evidence frame, provenance, instrument metadata and unit-neutral uncertainty round-trip;
- pending and confirmed measurements survive reopen;
- unknown storage schema and corrupt payload fail closed;
- service depends on the repository Protocol while in-memory behavior remains available.

No shared contract or downstream normalization change is imported.

### Chat 3 — accepted with selective replay

Accepted capability: explicit `UncertaintyAwareConstraintTolerancePolicy` and `UncertaintyAwareConstraintResolver`.

The policy widens only directly grounded linear residual tolerances:

- EQUAL circle radius/diameter-derived radius uncertainty;
- EQUAL line intrinsic linear uncertainty;
- CONCENTRIC verified center-distance uncertainty.

Missing relevant uncertainty preserves baseline behavior; unsupported relation classes do not receive fabricated uncertainty. The default `ConstraintResolver` remains unchanged. The existing residual confidence model intentionally consumes the effective tolerance, while candidate/entity confidence values remain immutable and final confidence remains the existing minimum gate.

### Chat 4 — accepted after Orchestrator-1 fixes

Accepted worker capability: explicit `mrea.solidworks-dimension-rules.v1`, Python fail-closed dimension-shape preflight, fingerprint inclusion, and matching C# pre-COM request-envelope validation for DISTANCE / DIAMETER / RADIUS / ANGLE shape rules.

Two integration/documentation defects were found and corrected in the rebuilt candidate:

1. **Standing qualification fingerprint omission.** Round 13 introduces `src/mrea_cad_bridge/solidworks_dimension_capabilities.py`, and that file affects the worker capability fingerprint. Current `compute_host_boundary_fingerprint(...)` did not include the new file, so a future edit to dimension rules could leave an earlier host qualification apparently reusable. The file is added to `HOST_BOUNDARY_FILES`, and a contract regression guard is added.
2. **Retired per-round host-status reporting.** Worker Pass-13 documentation repeated the legacy three-line host gate assignments even though current central policy retired those fields. The candidate documentation now points only to the dedicated `SOLIDWORKS_HOST_QUALIFICATION` workflow authority and explains fingerprint invalidation without fabricating a host result.

Because Pass 13 changes fingerprinted host-boundary files and adds a new fingerprinted capability file, a positive qualification generated for an older boundary fingerprint does not positively qualify this candidate. Re-run the dedicated host workflow only when positive real-host qualification is required. This is not an ordinary software-round blocker.

### Chat 5 — accepted with selective replay

Accepted capability: generation-bound read-only lifecycle sessions.

`_SnapshotGuardedConnection` verifies authoritative snapshot version, read-model version, snapshot schema and relational schema before repository statements; `_SnapshotGuardedCursor` verifies again after row consumption. Drift raises `LifecycleReadOnlyStaleError` and requires explicit refresh rather than silently serving generation N+1 under a session labeled N.

The design deliberately avoids pinning a long-lived SQLite read transaction that could block writers in rollback-journal mode.

## Replay policy

The rebuilt candidate starts from frozen current `main` and imports only reviewed worker-owned product/document/test surfaces. Worker `ORCHESTRATOR_HANDOFF.md` and `ORCHESTRATOR_DIRECTIVE.md` files are not replayed.

The five central commits that followed the workers' historical base changed orchestration and standing SOLIDWORKS qualification control-plane state; those current-main changes remain authoritative and are preserved.

Shared canonical contracts are not changed by worker replay. The only central/shared change made by Orchestrator 1 is the qualification-fingerprint completeness correction plus its regression test.

## Standing SOLIDWORKS qualification authority

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

No software-only test result is interpreted as positive real-host qualification.

## Final-review protocol

The exact rebuilt candidate SHA and exact-head CI evidence are recorded in the active integration PR conversation after GitHub Actions complete. A later or stale candidate SHA must not be substituted without a new exact-head audit.

```text
ROUND_13_ORCHESTRATOR1_AUDIT_PENDING_EXACT_HEAD_CI = TRUE
ORCHESTRATOR2_FINAL_REVIEW_REQUIRED = TRUE
MERGE_TO_MAIN_AUTHORIZED_BY_ORCHESTRATOR1 = FALSE
```
