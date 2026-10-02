# Round 18 — Orchestrator 2 Independent Audit

**Date:** 2026-10-02  
**Role:** Orchestrator 2 / 3  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`

## Authority rule

This audit was reconstructed from current remote GitHub state. Previous orchestrator prose was not accepted as authority. Evidence order:

1. current remote refs and exact commit/tree identity;
2. actual source and compare/diff;
3. actual GitHub Actions jobs;
4. accepted `main` orchestration state and canonical contracts;
5. worker/orchestrator documentation.

## Frozen accepted baseline

At audit start:

```text
main = af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223
tree = 0dc382bad0001119b078fd6fc43e7932d693f6c6
```

`chat_6_orchestrator/ORCHESTRATION_STATE.md` on that exact baseline states:

```text
ROUND_17_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

## Worker refs independently frozen

```text
Chat 1  chat-1/pass-18   3d54f3894dede142c75251c2483e70b5923c07fe
Chat 2  chat-2/pass-18   391928097236e2718f8726dd38f3e66e2fac140e
Chat 3  chat-3/pass-18   48ae8be29fb2fa5cb398d6d0e0bde3fae92252ac
Chat 4  chat-4/pass-18   4646ea5e344884716c589a4f43b717f9eccae10e
Chat 4b chat-4b/pass-18  e38fca4d30dbcac75757131f986c929138b3b475
Chat 5  chat-5/pass-18   9d0be957040d00f6574d134aac638a9e8b970bda
```

Every ref was independently compared to the accepted baseline. Every merge base equals exact `main` above and every branch is `behind_by = 0`.

The integration candidate was also compared directly to `main`. Worker handoff/control files were not present in the product integration delta. No `.github`, shared `core` contract, root integration-test, central directive/state, or Chat-8 mutation was introduced by the worker product integration.

## Independent slice review

### Chat 1 — preparation-aware guided capture

Reviewed the actual composition service against existing `GuidedCaptureReadinessService` and Pass-17 preparation policy.

The new surface:

- gates only clean-reference capture/recapture actions through preparation;
- reports `CHECK_PREPARATION` when required setup evidence is absent;
- requires the preparation observation to match the exact guided target view;
- preserves all non-capture guided actions without manufacturing setup evidence;
- remains read-only guidance and does not promote setup observations to metrology truth.

No confirmed Round-18 software defect was found in this slice.

### Chat 2 — provider-independent feature-anchor snapping

Reviewed `anchor_selection.py`, current provenance enums, materialization boundary and tests.

The Pass-18 surface:

- keeps the raw operator pick separate from detected feature suggestions;
- accepts only `VISION_DETECTED` advisory targets;
- scopes targets to the same view and reference frame;
- proposes only a unique nearest target inside the explicit pixel radius;
- fails closed on equal-distance ambiguity, duplicate target IDs and invalid coordinates/radius;
- requires `explicit_user_confirmation=True` before accepting a snap;
- records accepted detector provenance as `VISION_DETECTED` plus separate `USER_CONFIRMED`, rather than relabelling detector output as manual truth;
- keeps a non-snapped decision as `MANUAL_MEASURED`.

Durable persistence of `FeatureAnchorSelection` provenance is explicitly outside this Pass-18 migration; the implementation does not falsely claim it has been added to `FeatureAnchor` or canonical `MeasurementPackage`.

No confirmed Round-18 software defect was found in this slice.

### Chat 3 — Arc contact freedom diagnosis

Reviewed the topology-witness policy and numerical equations against the base local-DOF analyzer.

The new policy:

- accepts Arc-related entity-only `COINCIDENT` only with a unique endpoint-to-endpoint witness;
- requires finite Line-Arc tangent contact to be strictly inside both the finite line and Arc trim span;
- requires exactly one current external/internal round-round tangent branch;
- requires the derived contact to lie inside every participating Arc trim span;
- fails closed on missing, ambiguous, boundary or degenerate witnesses;
- does not move geometry or rewrite verified measurement truth.

The branch selection used by the underlying round-round equation is consistent with the policy's unique-compatible-branch guard: a different lower-error branch could not be selected without also entering the policy's ambiguous/no-witness fail-closed case.

No confirmed Round-18 software defect was found in this slice.

### Chat 4 — native SOLIDWORKS artifact request correlation

Reviewed `solidworks_agent.py`, the worker naming convention and Pass-18 negative tests.

The request-correlation requirement in this pass is specifically cross-`SketchPackage` identity, not a new per-attempt nonce. The successful response must contain exactly one `SOLIDWORKS_PART` whose ID is exactly:

```text
SWPART-{request.sketch_package_id}
```

A structurally valid artifact for another SketchPackage is rejected without rewriting or rebinding it. This matches the existing C# worker identity convention and the stated Pass-18 scope.

No confirmed Round-18 software defect was found in this slice.

### Chat 4b — finite SOLIDWORKS read-back values

Reviewed the actual C# host-boundary code.

`GetSystemValue3(...)` is now normalized only from a scalar `double` or a one-element COM array containing a `double`. Null, unexpected array shape/type, `NaN` and infinities raise before read-back evidence can be emitted. Successful finite values are then converted through the requested canonical unit.

This is a software fail-closed improvement; it is not positive real-host qualification evidence.

No confirmed Round-18 software defect was found in this slice.

### Chat 5 — deterministic physical field status

A confirmed integrity defect was found.

The Pass-18 field-status contract says the complete durable timeline must be checked for supported physical lifecycle event vocabulary before status is emitted. The worker implementation checked identity, sequence and time across the whole timeline, but converted/validated `event_type` only for `timeline[-1]`.

Consequently a corrupt timeline such as:

```text
UNKNOWN_EVENT (sequence 1)
ACTIVATED     (sequence 2)
```

could incorrectly return `ACTIVE`, hiding corruption in earlier committed history.

#### Orchestrator-2 repair

`field_status.py` was changed so every event in the complete timeline is converted to `PhysicalLifecycleEventType` and required to exist in the explicit `_STATE_BY_EVENT` projection before any current status is returned.

A dedicated regression test was added:

```text
chat_5_lifecycle_engineering_knowledge/tests/test_field_status_history_vocabulary.py
```

It proves that an unknown historical event followed by a valid latest event fails closed with `LifecycleKnowledgeIntegrityError`.

Repair commits before this audit record:

```text
2a5c6122f0d32c167b5322744d34cf036d33c4a0
ed2475f63e3c565af7da253c55a7f40a94233ad2
```

Repair-head tree:

```text
f296e67cfacef377cdfdf2ac19d3175d9cb7ca01
```

## Repair-head verification

The exact repair head `ed2475f63e3c565af7da253c55a7f40a94233ad2` passed the complete repository software suites:

```text
MREA CI              36949159910  SUCCESS  11/11 jobs executed
Round 4 Truth CI     36949159921  SUCCESS   6/6 jobs executed
```

Both normal and truth golden paths actually executed and succeeded. No mandatory job was accepted through skipped/cancelled state.

This audit record itself advances the branch again, so those runs are repair evidence only. Final Orchestrator-2 acceptance requires fresh CI on the post-audit exact SHA.

## SOLIDWORKS host authority

Round 18 changes fingerprinted host-boundary source, including `SolidWorksTransfer.cs` and `solidworks_agent.py`.

Real-host qualification remains owned by:

```text
.github/workflows/solidworks_host_qualification.yml
```

Software CI, mocks and static tests are not positive SOLIDWORKS-2026 host evidence. Any positive host claim must use dedicated qualification evidence matching the current source/boundary fingerprint and controlled host.

This is not a Round-18 software-integration blocker.

## Orchestrator-2 pre-final state

```text
ROUND18_ORCHESTRATOR2_CONFIRMED_DEFECTS = 1
ROUND18_ORCHESTRATOR2_CONFIRMED_DEFECT_1 = CHAT5_HISTORICAL_EVENT_VOCABULARY_NOT_VALIDATED
ROUND18_ORCHESTRATOR2_DEFECT_1_REPAIRED = TRUE
ROUND18_ORCHESTRATOR2_REPAIR_HEAD = ed2475f63e3c565af7da253c55a7f40a94233ad2
ROUND18_ORCHESTRATOR2_REPAIR_HEAD_CI = GREEN
ROUND18_ORCHESTRATOR2_FINAL_EXACT_HEAD_CI = PENDING_AFTER_AUDIT_COMMIT
ORCHESTRATOR3_FINAL_REVIEW_REQUIRED = TRUE
MERGE_TO_MAIN_AUTHORIZED_BY_ORCHESTRATOR2 = FALSE
SOLIDWORKS_REAL_HOST_POSITIVE_CLAIM = DEDICATED_MATCHING_FINGERPRINT_EVIDENCE_ONLY
```
