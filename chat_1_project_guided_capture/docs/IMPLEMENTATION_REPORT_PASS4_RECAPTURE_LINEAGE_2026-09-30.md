# Chat 1 — Pass 4 Immutable Recapture Lineage Implementation Report

**Date:** 2026-09-30  
**Branch:** `chat-1/pass-4`  
**Status:** isolated future-work delta; not represented as accepted/integrated while Round 3 remains open

## Implemented

### Persistence model

- `CaptureViewProgress.active_clean_reference_frame_id`;
- `FrameRecord.supersedes_frame_id`;
- `FrameRecord.source_clean_reference_frame_id`;
- migration/backfill for legacy single-clean sessions;
- validation of clean lineage, active leaf, measurement provenance and derived-evidence source consistency.

### Shared internal selector

Added `src/mrea_capture/lineage.py` with deterministic selectors for:

- active clean reference;
- active calibration;
- active rectification;
- active-attempt measurement frames.

### Capture service

Added `CaptureSessionService.recapture_clean_reference(...)`.

It:

1. requires an existing active clean reference;
2. refuses silent recapture of an accepted view;
3. writes a new immutable artifact;
4. records `supersedes_frame_id`;
5. advances the active pointer;
6. leaves old evidence untouched.

New measurement frames record the exact active clean source.

### Derived services

`CalibrationService`, `CaptureQualityService` and `RectificationService` now work against the active clean-reference attempt. A prior attempt's derived evidence does not block deriving evidence for a newer attempt.

### Guided Capture

`QUALITY_REJECTED` and strict WARN now return `RECAPTURE_CLEAN_REFERENCE`, making recovery executable rather than a dead-end `RESOLVE_QUALITY` state. After recapture, readiness correctly returns `RUN_CALIBRATION`.

### Canonical package

`CanonicalContractBuilder` emits only active-attempt evidence. Historical evidence stays persisted internally. No `mrea.capture-package.v1` schema change is required.

## Tests

Added `tests/test_recapture.py` covering:

1. full v1 -> recapture -> v2 lineage;
2. old artifact/evidence preservation;
3. active guidance reset after recapture;
4. second calibration/quality/rectification allowed for the new source frame;
5. canonical package exports only v2 clean + v2 measurement + v2 calibration;
6. rejected quality produces executable recapture action;
7. legacy lineage migration;
8. recapture after acceptance fails closed.

Updated guidance tests for the executable recapture action.

Schema-independent local regression:

```text
28 passed in 0.27s
```

The three schema-coupled tests also execute their capture/calibration/rectification/canonical behavior successfully and fail only when the archive-restored workspace attempts to open missing repository-root `core/contracts/mrea_contracts_v1.schema.json`.

## Ownership / contract impact

None outside Chat 1.

- no `core/contracts` change;
- no Chat-6 CI change;
- no Chat 2–5 change;
- no physical measurement semantics;
- no geometry inference;
- no silent deletion or overwrite of evidence.
