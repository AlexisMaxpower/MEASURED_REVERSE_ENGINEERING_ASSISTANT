# ORCHESTRATOR HANDOFF — Chat 1

**Pass:** 4  
**Directive:** `OD-2026-09-30-004`  
**Branch:** `chat-1/pass-4`  
**Accepted central baseline:** `bffc1dec2fe63c12b69a50c4bf348ef7df4cf662`  
**Implementation / pre-handoff SHA:** `1bd52e0a6c339e8f68fbae4d9005c8df86824e31`  
**Contract baseline:** `mrea.contracts.v1`  
**Date:** 2026-09-30  
**From:** Chat 1 — Project & Guided Capture  
**To:** Chat 6 — Orchestrator / Repository Integrator

## Completion state

```text
CHAT_1_PASS_4 = HANDOFF_PUBLISHED_AND_FROZEN
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```

This handoff is the final Pass-4 branch mutation. After publication, `chat-1/pass-4` is frozen. No further code or documentation may be pushed to this branch unless Chat 6 explicitly returns `FIX_REQUIRED`.

## Delivered Pass-4 scope

Pass 4 hardens Guided Capture around immutable capture generations without changing canonical wire contracts or moving downstream ownership into Chat 1.

### 1. Guided Capture readiness / next-action orchestration

Added deterministic readiness projection across the existing evidence pipeline:

```text
clean reference
-> calibration
-> quality
-> measurement frame
-> explicit view acceptance
-> required-view completion
```

The readiness layer:

- preserves CapturePlan order;
- distinguishes required vs optional views;
- blocks on quality `REJECT`;
- makes WARN policy explicit;
- returns machine-readable next actions and blockers;
- does not create measurement, geometry or CAD truth.

### 2. Immutable clean-reference recapture lineage

A rejected/obsolete clean reference is never silently replaced.

Pass 4 adds:

- `CaptureViewProgress.active_clean_reference_frame_id`;
- `FrameRecord.supersedes_frame_id` for clean-reference generations;
- `FrameRecord.source_clean_reference_frame_id` for measurement-frame provenance;
- `CaptureSessionService.recapture_clean_reference(...)`;
- source-aware calibration / quality / rectification lookup;
- active-generation filtering at the canonical `CapturePackage v1` adapter.

Recapture creates a new immutable artifact and links it to the previous clean reference. Historical clean/calibration/quality/rectification/measurement evidence remains persisted.

### 3. Explicit accepted-view reopen / revision

Accepted evidence cannot be silently recaptured. A deliberate revision requires `reopen_view(...)` with an audit reason.

Added:

- `CaptureViewRevisionEvent`;
- `CaptureViewProgress.recapture_required`;
- immutable reason / reopen timestamp / previous acceptance timestamp / source clean-reference provenance;
- fail-closed re-acceptance until a fresh clean-reference generation actually exists.

Reopening clears completion state but does not delete or rewrite prior evidence.

### 4. Deterministic capture-attempt history projection

Added read-only `CaptureAttemptHistoryService` / attempt snapshots for UI and orchestration.

Each clean-reference generation is projected with its exact associated:

- calibration;
- quality result;
- rectified reference;
- measurement frames;
- revision events;
- predecessor/successor lineage;
- active/historical state.

Ordering follows supersession links, not timestamps. Malformed ambiguous lineage fails closed rather than being guessed.

## Canonical / ownership invariants

Pass 4 preserves the following invariants required by OD-004:

1. **No silent clean-reference replacement.** Every recapture is a new immutable generation with explicit supersession provenance.
2. **Measurement/reference provenance remains attributable.** Measurement frames carry the exact source clean-reference generation and the active canonical package emits only active-generation measurement evidence.
3. **Historical evidence is immutable.** Recapture/reopen does not delete old artifacts, calibration, quality, rectification, measurement frames or revision evidence.
4. **Verified physical facts are not mutated by Chat 1.** Chat 1 does not own or rewrite `PhysicalMeasurement`; recapture changes capture-context selection only.
5. **`CapturePackage v1` stays compatible.** No shared schema field was added or changed. The adapter keeps the same canonical structure and selects active-generation evidence internally.
6. **Ownership remains bounded.** No measurement semantics, geometry ownership or CAD ownership moved into Chat 1.

No `core/contracts`, canonical fixture, Chat-6-owned CI file or shared integration test was modified by this worker result.

## Canonical baseline inspection

During OD-004 completion the current branch was checked against the accepted Round-3/current shared contract baseline:

- `core/contracts/mrea_contracts_v1.schema.json` is byte-identical between the worker branch and current `main`;
- `tests/fixtures/contracts/capture_package_v1.json` is byte-identical between the worker branch and current `main`;
- `tests/integration/test_chat1_to_chat2_boundary.py` is byte-identical between the worker branch and current `main`;
- `CanonicalContractBuilder` retains `mrea.capture-package.v1` and changes only internal active-generation selection semantics.

The branch has historical ancestry drift outside Chat 1; Round-4 central integration must therefore follow the central plan and replay accepted **worker-owned files** onto current `main`, preserving current Chat-6-owned/shared files rather than merging the branch history wholesale.

## Required gate evidence

Authoritative pre-handoff workflow:

- workflow: `MREA CI`;
- run ID: `36719112956`;
- run number: `514`;
- event: `push`;
- exact head SHA: `1bd52e0a6c339e8f68fbae4d9005c8df86824e31`;
- conclusion: **SUCCESS**.

OD-004 required gates on that exact pre-handoff SHA:

- `Contracts / canonical fixtures` — **SUCCESS**;
- `Chat 1 / Capture` — **SUCCESS**;
- `Integration / Chat 1 -> Chat 2` — **SUCCESS**.

Other slice jobs executed by the same workflow also succeeded; unrelated boundary jobs were conditionally skipped according to branch policy.

Historical local worker evidence before full-repository CI included `37 passed` for the schema-independent Chat-1 regression. Full-repository GitHub Actions above is the authoritative Pass-4 worker gate evidence.

## Worker-owned Pass-4 changed files

### Runtime / adapters

- `src/mrea_capture/__init__.py`
- `src/mrea_capture/calibration.py`
- `src/mrea_capture/contracts.py`
- `src/mrea_capture/guidance.py`
- `src/mrea_capture/history.py`
- `src/mrea_capture/lineage.py`
- `src/mrea_capture/models.py`
- `src/mrea_capture/quality.py`
- `src/mrea_capture/rectification.py`
- `src/mrea_capture/services.py`

### Tests

- `tests/test_guidance.py`
- `tests/test_recapture.py`
- `tests/test_reopen.py`
- `tests/test_attempt_history.py`

### Pass-4 engineering documentation

- `README.md`
- `docs/BUILD_REUSE_CHECK_PASS4_GUIDED_READINESS.md`
- `docs/IMPLEMENTATION_REPORT_PASS4_GUIDED_READINESS_2026-09-30.md`
- `docs/BUILD_REUSE_CHECK_PASS4_RECAPTURE_LINEAGE.md`
- `docs/IMPLEMENTATION_REPORT_PASS4_RECAPTURE_LINEAGE_2026-09-30.md`
- `docs/BUILD_REUSE_CHECK_PASS4_REOPEN_REVISION.md`
- `docs/IMPLEMENTATION_REPORT_PASS4_REOPEN_REVISION_2026-09-30.md`
- `docs/BUILD_REUSE_CHECK_PASS4_ATTEMPT_HISTORY.md`
- `docs/IMPLEMENTATION_REPORT_PASS4_ATTEMPT_HISTORY_2026-09-30.md`
- `docs/IMPLEMENTATION_STATE.md`
- `docs/PASS4_PROVISIONAL_HANDOFF.md` — retained as a historical/superseded provisional record
- `docs/COORDINATION_CHECKPOINT_PASS5_2026-09-30.md` — historical branch coordination artifact; not required for central product-code replay
- `ORCHESTRATOR_HANDOFF.md` — this final freeze commit

`ORCHESTRATOR_DIRECTIVE.md` is Chat-6-owned and must remain the current central version during replay; it is not a worker-owned delta.

## Known limitations / integration notes

- The worker branch predates later non-Chat1 updates and is historically diverged from current `main`. Do **not** whole-merge or whole-directory-replace it. Follow the Round-4 file-level replay plan.
- The required worker CI gates are green on the exact pre-handoff branch SHA. Current-main Chat 2 has newer worker-owned implementation than the Chat-2 tree in this branch ancestry; full replay composition against the then-current main belongs to Round-4 Stage 2.
- The shared canonical schema, capture fixture and Chat1->Chat2 boundary test used by this result are byte-identical to current main at OD-004 completion.
- Capture-quality thresholds are deterministic software defaults, not yet calibrated on a representative real-device dataset.
- Printed Measurement Mat physical-accuracy validation, lens/intrinsics strategy and native/mobile camera runtime validation remain open.
- Capture-attempt history is an internal read model, not a new canonical wire contract.
- No Stage-1 acceptance is claimed by this handoff.

## Open Change Requests

None.

## Acceptance requested from Chat 6

Please independently verify the selected Pass-4 worker-owned replay set, especially:

1. active clean-reference generation and supersession provenance;
2. source-clean binding for measurement frames;
3. active-generation-only `CapturePackage v1` serialization;
4. immutable historical evidence across recapture/reopen;
5. no mutation or strengthening of downstream verified physical facts;
6. current-main replay through the Round-4 Chat1->Chat2 provenance gate.

**Freeze state:** `chat-1/pass-4` is frozen immediately after this handoff commit. Further mutation requires an explicit Chat 6 `FIX_REQUIRED` verdict.
