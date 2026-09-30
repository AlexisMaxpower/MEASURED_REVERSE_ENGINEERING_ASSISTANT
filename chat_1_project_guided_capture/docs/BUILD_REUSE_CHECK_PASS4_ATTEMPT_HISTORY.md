# Build / Reuse Check — Pass 4 Capture Attempt History Projection

**Date:** 2026-09-30  
**Slice:** Chat 1 — Project & Guided Capture  
**Status:** isolated future-work package pending official next Chat 1 directive

## Problem

After immutable recapture and explicit reopen/revision, `CaptureSession` intentionally keeps historical clean references and all evidence derived from them. The persisted model is truthful, but consumers should not need to reconstruct supersession chains and evidence ownership ad hoc.

Without one deterministic projection, a UI or orchestrator can accidentally mix calibration, quality, rectification or measurement evidence from different capture attempts.

## Reuse

Reuse existing Chat 1 provenance:

- clean-reference `supersedes_frame_id`;
- per-view `active_clean_reference_frame_id`;
- measurement `source_clean_reference_frame_id`;
- calibration / quality / rectification `source_frame_id`;
- revision events;
- immutable artifact IDs and SHA-256 values.

No external dependency is required.

## Build

Added `history.py` with a read-only `CaptureAttemptHistoryService` and internal projection DTOs:

- `CaptureAttemptSnapshot`;
- `CaptureViewAttemptHistory`;
- `CaptureAttemptHistoryError`.

For each view it returns an ordered lineage:

```text
attempt 1 -> attempt 2 -> ... -> active attempt
```

Each attempt contains:

- clean-reference frame/artifact identity;
- supersedes / superseded-by links;
- active flag;
- acceptance timestamp when known;
- revision-event IDs;
- calibration ID;
- quality analysis ID + verdict;
- rectified-reference ID;
- measurement-frame IDs.

`project_session(...)` preserves CapturePlan/view ordering.

## Determinism / fail-closed

Lineage order is derived from explicit supersession links, not timestamps.

The persisted `CaptureSession` validator is strengthened so one view cannot silently contain multiple clean-reference roots or disconnected lineage components. History projection also fails closed on missing predecessors, branching, cycles or disconnected chains.

## Truth boundary

This is a read-only internal projection. It does not:

- mutate `CaptureSession`;
- change active evidence;
- alter canonical `CapturePackage v1`;
- create measurement or geometry truth;
- delete historical artifacts.
