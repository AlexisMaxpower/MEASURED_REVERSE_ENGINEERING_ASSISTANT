# Round 14 — Orchestrator 1 Audit

**Date:** 2026-10-01  
**Role:** Orchestrator 1 / first managerial audit  
**Frozen shared base:** `main` @ `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`

## Audit method

This audit was performed from live GitHub repository state after the parallel worker slice. Worker chat answers were not treated as authority. Branch ancestry, changed-file scope, source code, tests, current central control-plane documents and exact GitHub Actions results are the evidence plane.

All five Pass-14 worker branches have merge-base exactly equal to the current frozen Round-13 closure `main`. None is behind `main`. The integration candidate is nevertheless rebuilt centrally so worker handoff files are not promoted as product/control state and so cross-slice repairs can be added without blind branch merges.

## Frozen worker heads

```text
Chat 1  chat-1/pass-14  a328adb2644ff29d5b55924a6e36d7cc7c22f8bd
Chat 2  chat-2/pass-14  c2b2cd659c1adfb4ba5ebb2a18c070ca7a1e1c48
Chat 3  chat-3/pass-14  889023452bd1ddc5a4287a2c2998547934271b81
Chat 4  chat-4/pass-14  91c374044f31ab7be9e143c4e8cb244ad45a4a52
Chat 5  chat-5/pass-14  515d6a37777bcfbf0ec971c684d10eba4797ac7d
```

## Worker-slice review

### Chat 1 — accepted with selective replay

Accepted capability: `CaptureQualityLifecycleService`, synchronizing persisted quality evidence with internal capture-view lifecycle without changing canonical CapturePackage truth.

Reviewed properties:

- ACCEPT/WARN keep the active view `CAPTURED`;
- REJECT returns the view to `IN_PROGRESS` without deleting evidence;
- accepted views require explicit reopen before reanalysis;
- a REJECT on the active clean reference blocks the quality-aware acceptance facade;
- absence of a quality result remains backward-compatible because policy, not this facade, decides whether analysis is mandatory;
- active clean-reference lineage is rechecked after quality persistence before lifecycle state is changed.

### Chat 2 — accepted with selective replay

Accepted capability: deterministic durable measurement-session enumeration through the existing repository boundary.

Reviewed properties:

- in-memory and SQLite repositories implement the same `list_sessions(...)` contract;
- optional project scoping is normalized and rejects blank filters;
- ordering is newest-first with deterministic session-id tie-breaking;
- SQLite rows are decoded through the same fail-closed persisted-session codec used by direct lookup;
- existing uncertainty compatibility remains lossless because deserialization reconstructs neutral uncertainty and the domain model derives `uncertainty_mm` only for millimetre measurements.

No shared contract is changed.

### Chat 3 — accepted with selective replay

Accepted capability: uncertainty-aware verified-measurement contradiction policy integrated into the opt-in uncertainty-aware constraint resolver.

Reviewed properties:

- only existing supported EQUAL intrinsic-metric and CONCENTRIC center-distance contradiction gates are relaxed;
- explicit verified uncertainty can enlarge the measurement allowance;
- missing uncertainty preserves baseline fixed-tolerance behavior rather than inventing confidence;
- diameter uncertainty is converted to radius uncertainty consistently with value conversion;
- unrelated relation classes and unverified dimensions do not influence the contradiction gate;
- the default `ConstraintResolver` remains unchanged.

### Chat 4 — accepted after central control-plane reinforcement

Accepted capability: explicit `mrea.solidworks-entity-rules.v1`, Python fail-closed entity preflight and matching C# pre-COM entity-envelope validation for POINT / LINE / CIRCLE / ARC geometry.

Reviewed properties:

- required coordinates and numeric geometry are checked before worker invocation / COM startup;
- entity IDs are required and duplicate IDs fail closed;
- line degeneracy, radius validity and zero/full-circle ARC spans fail before COM mutation;
- worker capability projection includes the entity-rule object so rule changes alter the Python/C# compatibility fingerprint;
- `solidworks_entity_capabilities.py` is included in `HOST_BOUNDARY_FILES`, so Round 14 changes invalidate older host-boundary fingerprints.

Central integration finding: the shared qualification regression test still asserted only Pass-13 dimension-rule fingerprint coverage. Orchestrator 1 adds an explicit regression test requiring `solidworks_entity_capabilities.py` to remain part of the standing host-boundary fingerprint.

Round 14 changes fingerprinted SOLIDWORKS host-boundary code. Positive real-host qualification is valid only for a matching fingerprint; software CI is not positive host qualification and the standing workflow remains the dynamic authority.

### Chat 5 — accepted with selective replay

Accepted capability: durable snapshot-bound revision comparison exposed through the read-only engineering-knowledge repository and local GET-only HTTP API.

Reviewed properties:

- both revisions must exist and belong to the same part;
- materials, failure/test counts and lifecycle state are derived from committed relational facts;
- durable lifecycle-state projection mirrors the existing in-memory semantics, including failure/reinstall handling;
- all SQL reads use the existing snapshot-guarded connection, so generation drift fails closed;
- HTTP serialization remains factual and deterministic and introduces no ranking, recommendation or inferred causality.

## Central integration defect and repair

The first rebuilt Round-14 candidate exposed a pre-existing shared CI defect: `.github/workflows/round4_truth.yml` was hard-coded to the historical branch name `integration/pass-4-candidate`.

Consequences on the correct new branch `integration/pass-14-candidate` were unacceptable for certification:

- push Truth CI did not start at all because the push branch filter excluded the branch;
- pull-request Truth CI could start its shared job but the actual boundary/golden jobs were guarded by exact `integration/pass-4-candidate` checks and would be skipped.

Orchestrator 1 repairs the workflow to accept versioned integration candidate branches through `integration/pass-*-candidate` and matching `startsWith(...)`/`endsWith(...)` guards. A central contract regression test prevents reintroduction of the single historical branch lock.

The superseded pre-repair candidate is not certification evidence. Only the post-repair exact SHA may be accepted after fresh push and PR CI.

## Replay policy

The rebuilt candidate starts from the frozen current `main` and imports reviewed worker-owned product/document/test surfaces from all five workers. Worker `ORCHESTRATOR_HANDOFF.md` files are restored to the frozen-main versions and are not used as integration authority.

No shared canonical contract is imported from a worker branch. Central changes made by Orchestrator 1 are:

1. host-boundary regression coverage for the new entity capability rules;
2. generic integration-candidate support in the standing Truth CI workflow plus regression coverage;
3. this audit record.

## Standing SOLIDWORKS qualification authority

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED
```

Round 14 changes the fingerprinted host boundary, therefore an older qualification manifest is reusable only if its recorded fingerprint equals the candidate's current host-boundary fingerprint.

## Final-review protocol

The exact post-repair candidate SHA and exact-head CI evidence are recorded in the active Round-14 integration PR conversation after GitHub Actions complete. A later SHA must not inherit this audit without new exact-head CI.

```text
ROUND_14_ORCHESTRATOR1_AUDIT_PENDING_EXACT_HEAD_CI = TRUE
ORCHESTRATOR2_FINAL_REVIEW_REQUIRED = TRUE
MERGE_TO_MAIN_AUTHORIZED_BY_ORCHESTRATOR1 = FALSE
```
