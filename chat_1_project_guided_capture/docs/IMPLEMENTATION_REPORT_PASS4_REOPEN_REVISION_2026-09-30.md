# Chat 1 — Pass 4 Explicit View Reopen / Revision Implementation Report

**Date:** 2026-09-30  
**Branch:** `chat-1/pass-4`  
**Status:** isolated future-work delta; not represented as accepted OD-004 work

## Implemented

### Audit model

Added `CaptureViewRevisionEvent` with:

- stable `revision_id`;
- `view`;
- required non-empty `reason`;
- `reopened_at`;
- `previous_accepted_at`;
- `active_clean_reference_frame_id`.

`CaptureSession.revision_events` persists the audit trail and validates that referenced clean evidence belongs to the same view.

### Workflow gate

`CaptureViewProgress.recapture_required` marks an explicitly reopened view as incomplete until a new clean-reference attempt is captured.

`CaptureSessionService.reopen_view(...)`:

1. requires the view to be accepted;
2. requires an active clean reference;
3. validates reason and timestamp;
4. appends immutable revision evidence;
5. moves status back to `CAPTURED`;
6. clears `accepted_at` and session `completed_at`;
7. sets `recapture_required=True`.

`accept_view(...)` fails closed while that gate is active.

`recapture_clean_reference(...)` clears the gate only after the replacement clean artifact has actually been stored and activated.

### Guided Capture

A reopened view now produces:

- action: `RECAPTURE_CLEAN_REFERENCE`;
- blocker: `VIEW_REOPENED_RECAPTURE_REQUIRED`.

After recapture, the active attempt has no derived evidence yet, so readiness correctly returns `RUN_CALIBRATION`.

### Canonical boundary

No `CapturePackage v1` change. Revision/audit state remains internal Chat 1 provenance.

## Tests

Added `tests/test_reopen.py` covering:

1. accepted view -> explicit reopen audit event;
2. session completion reset;
3. deterministic readiness blocker/action;
4. re-acceptance blocked before fresh clean reference;
5. reopen -> recapture clears the gate;
6. previous artifact remains intact;
7. reopen requires accepted state and non-empty reason;
8. reopen timestamp cannot precede original acceptance.

Schema-independent regression including quality:

```text
33 passed in 0.32s
```

## Ownership

No changes outside Chat 1. No shared contracts, CI, measurement semantics or geometry semantics were modified.
