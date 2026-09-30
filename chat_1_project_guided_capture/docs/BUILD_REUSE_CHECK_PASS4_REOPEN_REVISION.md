# Build / Reuse Check — Pass 4 Explicit View Reopen / Revision

**Date:** 2026-09-30  
**Slice:** Chat 1 — Project & Guided Capture  
**Status:** isolated future-work package pending official next Chat 1 directive

## Problem

Immutable recapture correctly refuses to replace an already accepted view. Without an explicit reopen operation, however, a user cannot intentionally revise an accepted capture after discovering a setup, focus, framing or evidence problem.

## Reuse

Reuse existing Chat 1 primitives:

- `CaptureSession` persistence;
- active clean-reference lineage;
- immutable artifact history;
- `CaptureViewStatus`;
- Guided Capture readiness;
- existing content-addressed ArtifactStore.

No external dependency is required.

## Build

MREA-specific revision orchestration adds:

- `CaptureViewRevisionEvent` audit record;
- `CaptureViewProgress.recapture_required` gate;
- `CaptureSession.revision_events` history;
- `CaptureSessionService.reopen_view(...)`;
- explicit guidance blocker `VIEW_REOPENED_RECAPTURE_REQUIRED`;
- fail-closed prevention of re-acceptance before a fresh clean-reference attempt.

## Provenance rules

Reopening does not delete or rewrite any evidence.

The revision event records:

- view;
- non-empty reason;
- reopen timestamp;
- previous acceptance timestamp;
- clean-reference frame that was active when the revision was requested.

The old accepted evidence remains queryable. A subsequent `recapture_clean_reference(...)` creates a new immutable clean attempt and clears only the workflow gate.

## Canonical boundary

No shared contract is changed. Revision events remain internal Chat 1 provenance and do not alter `CapturePackage v1`.

## Safety behavior

- only `ACCEPTED` views can be reopened;
- blank reason is rejected;
- reopen timestamp cannot precede original acceptance;
- reopening clears session completion when required work becomes active again;
- `accept_view(...)` fails while `recapture_required=True`;
- recapture clears the gate and restarts readiness at calibration for the new active clean frame.
