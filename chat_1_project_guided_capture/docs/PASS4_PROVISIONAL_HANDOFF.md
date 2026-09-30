# Chat 1 — Pass 4 Provisional Handoff (Historical / Superseded)

**Date:** 2026-09-30  
**Branch:** `chat-1/pass-4`  
**Status:** HISTORICAL PROVISIONAL RECORD — superseded by `OD-2026-09-30-004`; not the final handoff

## Historical context

This file records the pre-OD-004 provisional state of the branch and is retained only for audit continuity. Round 3 is now closed; Chat 1 Pass 3 is accepted, and `OD-2026-09-30-004` selects `chat-1/pass-4` for Round-4 Stage-1 intake.

The authoritative completion artifact is the root `ORCHESTRATOR_HANDOFF.md` published as the final Pass-4 branch mutation.

## Delivered future-work delta

- deterministic guided-capture readiness evaluation;
- machine-readable next-action and blocker codes;
- required/optional view completeness semantics;
- quality REJECT blocking and explicit WARN policy;
- canonical-boundary non-mutation test;
- no shared contract changes.

## Local evidence

`24 passed` in the schema-independent local regression set.

## OD-004 completion requirement

`OD-2026-09-30-004` is now active. Pass 4 must be checked against the accepted Round-3 contracts/baseline, required gates must be recorded, and a truthful root `ORCHESTRATOR_HANDOFF.md` must be published as the final commit. That commit freezes `chat-1/pass-4` pending Chat 6 review.


## Additional isolated delta — recapture lineage

The branch also closes the rejected-capture recovery gap:

- immutable clean-reference supersession chain;
- explicit active clean reference per view;
- measurement frames linked to their source clean attempt;
- old calibration/quality/rectification/measurement evidence preserved;
- active-attempt filtering at every Chat 1 service and canonical boundary;
- `RECAPTURE_CLEAN_REFERENCE` is now an executable guided action for rejected quality;
- legacy single-clean persisted sessions migrate deterministically.

No shared contract or Chat 2–5 file is modified. This delta is part of the selected Pass-4 worker cut and remains pending Chat 6 Stage-1 review.

## Additional isolated delta — explicit accepted-view revision

The branch also contains an audited reopen path for an already accepted view. A reopen records reason/timestamps/source clean provenance, resets completion, and requires a fresh clean reference before the view can be accepted again. This closes the safety gap identified by immutable recapture: accepted evidence cannot be silently replaced, but an intentional revision now has an explicit controlled path.

Local schema-independent regression including quality: `33 passed`.

## Additional isolated delta — capture attempt history

The branch now includes a deterministic, read-only capture-attempt history projection. It exposes active and historical attempts without mixing evidence across clean-reference generations and fails closed on ambiguous/malformed lineage instead of guessing attempt order.

Local schema-independent regression: `37 passed`. No shared contract is modified.
