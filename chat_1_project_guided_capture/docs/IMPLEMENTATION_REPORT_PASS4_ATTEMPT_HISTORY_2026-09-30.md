# Chat 1 — Pass 4 Capture Attempt History Implementation Report

**Date:** 2026-09-30  
**Branch:** `chat-1/pass-4`  
**Status:** isolated future-work delta; not represented as accepted OD-004 work

## Implemented

### Attempt-history projection

Added `CaptureAttemptHistoryService` to turn persisted immutable evidence into a deterministic per-view attempt history.

The projection exposes, per attempt:

- ordinal attempt number;
- clean-reference frame and artifact identity;
- predecessor/successor lineage;
- active state;
- acceptance/revision evidence;
- calibration;
- quality result/verdict;
- rectification;
- measurement frames.

This removes the need for UI/orchestration code to infer evidence ownership independently.

### Session-level projection

`project_session(...)` returns histories in persisted view/CapturePlan order, including views that have no capture attempt yet.

### Persisted lineage hardening

`CaptureSession` now rejects:

- more than one root clean reference for one view;
- disconnected clean-reference components;
- cycles in the clean-reference supersession chain.

The existing active-leaf, no-branch, same-view and evidence-source rules remain in force.

## Tests

Added `tests/test_attempt_history.py` covering:

1. one active attempt with calibration/quality/rectification/measurement evidence;
2. read-only projection (session remains byte/JSON-equivalent);
3. accepted attempt -> reopen -> recapture -> second attempt;
4. revision evidence stays attached to the historical attempt;
5. evidence from attempt 1 and attempt 2 never mixes;
6. session projection preserves view order;
7. views without attempts are explicit empty histories;
8. disconnected clean-reference roots fail closed.

Schema-independent regression:

```text
37 passed
```

A wider run produced 39 passing tests and 2 failures only at the final canonical-schema file load because the patch workspace does not contain repository-root `core/contracts/mrea_contracts_v1.schema.json`.

## Contract / ownership impact

None outside Chat 1.

- no `core/contracts` change;
- no shared CI change;
- no Chat 2–5 change;
- no measurement semantics;
- no geometry inference;
- no canonical wire-format change.
