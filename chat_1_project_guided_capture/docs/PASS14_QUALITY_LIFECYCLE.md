# Chat 1 — Pass 14 Quality/Lifecycle Synchronization

**Role:** Project & Guided Capture  
**Directive:** `OD-2026-10-01-007`  
**Branch:** `chat-1/pass-14`  
**Baseline:** `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`  
**Date:** 2026-10-01

## Problem

The accepted Chat-1 baseline already persisted deterministic capture-quality evidence and Guided Capture readiness, but quality verdicts did not synchronize the internal `CaptureViewStatus`. A rejected active clean reference could therefore remain marked `CAPTURED`, and a low-level acceptance call had no quality-aware fail-closed facade.

This is an internal Chat-1 lifecycle gap only. It is not a physical-measurement or shared-contract problem.

## Pass-14 slice

Pass 14 adds `quality_lifecycle.py` with `CaptureQualityLifecycleService`.

The service composes the existing immutable `CaptureQualityService` and `CaptureSessionService` rather than duplicating image-analysis logic.

### Status synchronization

After analysis of the active immutable clean-reference attempt:

```text
quality ACCEPT -> CaptureViewStatus.CAPTURED
quality WARN   -> CaptureViewStatus.CAPTURED
quality REJECT -> CaptureViewStatus.IN_PROGRESS
```

`REJECT` clears no evidence and deletes nothing. It only makes the internal lifecycle reflect that the view still needs work. A later `recapture_clean_reference(...)` creates a new immutable attempt and returns the view to `CAPTURED` as before.

Repeated analysis is idempotent and also repairs a stale persisted status from already-persisted quality evidence. This gives the two-step persistence path a deterministic recovery behavior.

### Quality-aware acceptance

`CaptureQualityLifecycleService.accept_view(...)` fails closed when the active clean-reference quality result is `REJECT`.

It does not require a quality result when none exists because the lower-level capture service remains backward-compatible and Guided Capture policy owns whether quality analysis is mandatory. WARN handling remains policy-controlled in `GuidedCaptureReadinessService`.

Accepted views cannot be silently reanalyzed through this facade; they must first use the existing explicit `reopen_view(...)` + recapture lineage.

## Truth boundaries

The new lifecycle synchronization remains diagnostic/internal:

- no `PhysicalMeasurement` is created or modified;
- no geometry, CAD or lifecycle-slice truth is inferred;
- no source image is rewritten;
- no historical quality evidence is deleted;
- no shared contract or canonical fixture changes;
- canonical `CapturePackage v1` is unchanged because view status and quality evidence remain internal.

## Tests

`tests/test_quality_lifecycle.py` covers:

1. ACCEPT/WARN/REJECT status mapping;
2. canonical CapturePackage byte-level data equivalence before/after status synchronization;
3. REJECT blocks quality-aware acceptance;
4. immutable recapture resets the lifecycle and a new passing attempt can be accepted;
5. repeated analysis repairs stale status without duplicating quality evidence;
6. accepted views require explicit reopen before quality reanalysis.

Full Chat-1 and adjacent boundary/contract gates are required before final handoff.
