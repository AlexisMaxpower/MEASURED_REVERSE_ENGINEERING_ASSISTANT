# Round 17 — Orchestrator 2 Independent Audit

**Date:** 2026-10-02  
**Role:** Orchestrator 2 / 3  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`

## Authority rule

This audit was performed from current remote GitHub state. Previous orchestrator prose was not accepted as evidence. The authority order used here is:

1. current remote refs and exact commit/tree identity;
2. actual source and diff;
3. actual GitHub Actions run/job execution;
4. canonical shared contracts and current orchestration directives;
5. worker/orchestrator documentation.

## Frozen baseline observed by Orchestrator 2

Central `main` at audit start:

```text
933d925c69944d40859ae1f9ff80d7a3ecb7f760
```

Main tree:

```text
a8bef61be966b4cc3ba05a1d43c4c432c17b1337
```

`chat_6_orchestrator/ORCHESTRATION_STATE.md` on that exact baseline states:

```text
ROUND_16_CLOSED = TRUE
OPEN_SOFTWARE_BLOCKERS = NONE
MERGE_TO_MAIN_COMPLETED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

The Round-17 integration branch was independently verified to have merge-base equal to that exact `main`, to be ahead only, and to contain no `.github`, `core/contracts`, root integration-test, central state/directive, or other shared-infrastructure mutation from the worker integration itself.

## Worker refs independently observed

```text
Chat 1  chat-1/pass-17   54b6317cc459dc6799572b726df9ac821a422f99
Chat 2  chat-2/pass-17   68c1a33838e2c59435fcdc6f762134e52bac8346
Chat 3  chat-3/pass-17   060215f5d7fe4e97271db6103d904e4ea8097220
Chat 4  chat-4/pass-17   345026a9fbd4455ddfd3d137a2fd85c046146103
Chat 4b chat-4b/pass-17  fc103ad5dd6ee506b5824a5f62ecae7dc89d30e2
Chat 5  chat-5/pass-17   a0e044736ef6a2e7a1d3ef330bd4f306c8038ec0
```

Each inspected worker ref has the Round-16 closure SHA above as its merge base and is `behind_by = 0` relative to that baseline. Chat 4 and Chat 4b overlap the same owned CAD slice, so their product deltas must be composed rather than history-merged blindly.

## Independent source review

### Chat 1 — prepared clean-reference gate

Reviewed the actual Pass-17 preparation/capture facade and tests.

- setup observations are explicitly operator-observed and are not promoted to physical measurement truth;
- `False` and missing (`None`) required preparation evidence block the clean-reference mutation;
- preparation is evaluated before calling the durable capture/recapture mutation;
- the new surface does not alter canonical measurement provenance or create metrology values.

No confirmed Round-17 software defect was found in this slice.

### Chat 2 — durable hands-free restart recovery

Reviewed `recovery.py`, the current hands-free controller, the actual durable `MeasurementSessionService`, and restart tests.

A specific possible failure mode was investigated independently: the recovery query selects matching unverified measurements, so an implementation that retained rejected candidates could have resurrected a rejected value after restart. The actual durable service was checked and `reject_candidate()` removes the rejected measurement from the session before saving it. Therefore the suspected resurrection defect is not present.

The implemented recovery also:

- resumes only an unverified candidate matching the exact measurement context;
- rejects an explicitly selected verified or context-mismatched candidate;
- fails closed when multiple pending candidates match unless an explicit ID is supplied;
- does not invent transient `AWAITING_VALUE`, `VERIFIED`, or `REJECTED` interaction state after restart.

No confirmed Round-17 software defect was found in this slice.

### Chat 3 — verified angular local-DOF policy

Reviewed the actual angle equation policy against the current Chat-3 directive requiring diagnostic-only, fail-closed DOF behavior.

The Pass-17 path:

- accepts only verified `ANGLE` dimensions in `deg` with exactly two line targets;
- requires a unique shared-endpoint topology witness;
- rejects missing/ambiguous witnesses and unsupported units;
- checks current geometry against the verified angle using explicit measurement uncertainty plus only the configured numerical witness tolerance;
- keeps endpoint-storage direction from changing the geometric ray semantics;
- uses a cross-product residual for the local 0/180-degree singular cases so the Jacobian does not silently lose the constraint;
- does not move geometry or rewrite the verified upstream measurement.

No unsupported topology was found being converted into an exact equation, confidence, or tolerance. No confirmed Round-17 software defect was found in this slice.

### Chat 4 — canonical artifact boundary

Reviewed `CadAdapterResult` artifact validation against the canonical `ArtifactReference` definition in `core/contracts/mrea_contracts_v1.schema.json` on the accepted baseline.

The required fields and allowed optional fields match the canonical v1 contract exactly:

```text
required: artifact_id, kind, uri
optional: media_type, sha256, metadata
additional properties: forbidden at ArtifactReference level
```

The Pass-17 code rejects malformed required fields, unknown top-level fields, malformed optional scalar fields, non-object metadata, and duplicate artifact IDs before the adapter result can be accepted. SOLIDWORKS parser errors at this boundary are normalized as adapter errors.

No confirmed Round-17 software defect was found in this slice.

### Chat 4b — SOLIDWORKS rebuild failure gate

Reviewed the actual C# host-boundary change.

Previously ignored `EditRebuild3()` return values are now checked at the final sketch rebuild and after accepted-constraint application. A failed rebuild raises before successful host transfer/read-back can be claimed.

This is a software fail-closed improvement. It is not real-host qualification evidence.

### Chat 5 — revision change explanation HTTP surface

Reviewed the actual read-only HTTP route, serializer, durable revision explanation source, and endpoint tests.

The new route:

```text
GET /v1/knowledge/revision-change-explanation
```

requires exactly one left and right revision ID, uses the snapshot-bound durable knowledge session, serializes the existing factual explanation model, rejects unexpected parameters/methods, and does not add ranking, recommendation, geometry derivation, or causal inference.

The source-backed record/artifact IDs remain those already owned by durable lifecycle facts. No confirmed Round-17 software defect was found in this slice.

## Canonical and integration boundaries

The Round-17 worker delta does not modify canonical shared contracts. Actual normal and truth CI on the pre-audit exact candidate executed the shared contract job, all five primary slice jobs, all four adjacent integration jobs, and both golden paths successfully. This audit file changes the integration head, so those older runs are historical evidence only; final acceptance requires new exact-head CI after this commit.

## SOLIDWORKS standing qualification authority

The accepted central orchestration state defines real-host SOLIDWORKS qualification as an out-of-band environment qualification owned by:

```text
.github/workflows/solidworks_host_qualification.yml
```

That workflow checks out an exact source SHA on a controlled self-hosted Windows/SOLIDWORKS-2026 runner and emits `solidworks_host_qualification.json` with a host-boundary fingerprint.

Round 17 changes the fingerprinted host-boundary file `chat_4_cad_bridge_verification/solidworks_agent/SolidWorksTransfer.cs`. Therefore software CI, mocks, static tests, or an older qualification with a different boundary fingerprint must not be used as positive real-host evidence. This is not an ordinary Round-17 software blocker; a positive host claim must be resolved from the dedicated workflow evidence for the matching boundary.

## Orchestrator-2 technical finding

No confirmed Round-17 product-code defect remained after independent inspection of the current remote source, worker baselines, canonical contract, durable measurement rejection semantics, angular topology policy, CAD artifact boundary, SOLIDWORKS fail-closed rebuild behavior, and lifecycle HTTP surface.

No speculative source change was introduced solely to manufacture an audit repair.

The only repository mutation performed by Orchestrator 2 is this durable audit record. Consequently the post-audit branch SHA is a new certification target and must pass exact-head CI before Orchestrator 2 can issue its final SHA verdict.

```text
ROUND17_ORCHESTRATOR2_SOURCE_REPAIR_REQUIRED = FALSE
ROUND17_ORCHESTRATOR2_AUDIT_RECORD_WRITTEN = TRUE
ROUND17_ORCHESTRATOR2_EXACT_HEAD_CI = PENDING_AFTER_AUDIT_COMMIT
ORCHESTRATOR3_FINAL_REVIEW_REQUIRED = TRUE
MERGE_TO_MAIN_AUTHORIZED_BY_ORCHESTRATOR2 = FALSE
SOLIDWORKS_REAL_HOST_POSITIVE_CLAIM = DEDICATED_MATCHING_FINGERPRINT_EVIDENCE_ONLY
```
