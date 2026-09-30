# Build / Reuse Check — Pass 4 Immutable Recapture Lineage

**Date:** 2026-09-30  
**Slice:** Chat 1 — Project & Guided Capture  
**Status:** isolated work package pending Round-3 closure / official next directive

## Problem

Guided quality can reject a clean-reference attempt. Before this delta, Chat 1 preserved evidence immutably but also enforced exactly one clean reference per view, leaving no safe recovery path.

## Reuse

No external library is required. Reuse existing:

- content-addressed `ArtifactStore`;
- `CaptureSession` persistence;
- calibration, rectification and quality source-frame provenance;
- canonical `CapturePackage v1`;
- guided readiness policy.

## Build

MREA-specific lineage policy is implemented locally:

- active clean-reference pointer per view;
- clean-reference `supersedes_frame_id`;
- measurement `source_clean_reference_frame_id`;
- deterministic legacy backfill when only one clean attempt exists;
- active-attempt selectors in `lineage.py`;
- explicit `recapture_clean_reference(...)`;
- active-attempt filtering in calibration, quality, rectification, readiness and canonical serialization.

## Truth / provenance rules

Recapture never overwrites or deletes prior evidence. Historical artifacts and derived evidence remain accessible in the session. Only the active-attempt pointer changes.

No old calibration, quality result, rectification or measurement frame is silently reused for a newer clean reference. Each derived item is accepted only when its `source_frame_id` matches the active clean frame.

## Canonical boundary

`CapturePackage v1` is unchanged. When multiple attempts exist internally, the builder emits:

- the active clean reference;
- calibration derived from that active clean reference, if present;
- only measurement frames explicitly tied to that active clean reference.

Historical attempts remain internal provenance and are not leaked as ambiguous duplicate view evidence.

## Safety constraint

An already accepted view cannot be recaptured silently. A future explicit reopen/revision workflow is required for that state transition.
