# Chat 1 — Pass 4 Provisional Handoff

**Date:** 2026-09-30  
**Branch:** `chat-1/pass-4`  
**Status:** PROVISIONAL / ISOLATED — NOT AN OFFICIAL OD-004 ACCEPTANCE HANDOFF

## Why provisional

Round 3 is not yet closed. `main` still carries `OD-2026-09-29-003`, and Chat 8's current blocker belongs to Chat-6-owned post-merge golden-path CI coverage. Chat 1 Pass 3 must not be reopened for that defect.

This document records future Chat 1 work only so it can be inspected without pretending it is already accepted.

## Delivered future-work delta

- deterministic guided-capture readiness evaluation;
- machine-readable next-action and blocker codes;
- required/optional view completeness semantics;
- quality REJECT blocking and explicit WARN policy;
- canonical-boundary non-mutation test;
- no shared contract changes.

## Local evidence

`24 passed` in the schema-independent local regression set.

## Integration requirement

Before this work can be considered official Pass 4:

1. Round 3 must close;
2. Chat 6 must publish the next Chat 1 directive/baseline;
3. this branch must be rebased/reconstructed onto that accepted baseline if required;
4. full repository CI and Chat 1 -> Chat 2 boundary must be green;
5. only then should an official `ORCHESTRATOR_HANDOFF.md` be published/frozen.


## Additional isolated delta — recapture lineage

The branch also closes the rejected-capture recovery gap:

- immutable clean-reference supersession chain;
- explicit active clean reference per view;
- measurement frames linked to their source clean attempt;
- old calibration/quality/rectification/measurement evidence preserved;
- active-attempt filtering at every Chat 1 service and canonical boundary;
- `RECAPTURE_CLEAN_REFERENCE` is now an executable guided action for rejected quality;
- legacy single-clean persisted sessions migrate deterministically.

No shared contract or Chat 2–5 file is modified. This delta remains provisional until the official next Chat 1 directive.

## Additional isolated delta — explicit accepted-view revision

The branch also contains an audited reopen path for an already accepted view. A reopen records reason/timestamps/source clean provenance, resets completion, and requires a fresh clean reference before the view can be accepted again. This closes the safety gap identified by immutable recapture: accepted evidence cannot be silently replaced, but an intentional revision now has an explicit controlled path.

Local schema-independent regression including quality: `33 passed`.

## Additional isolated delta — capture attempt history

The branch now includes a deterministic, read-only capture-attempt history projection. It exposes active and historical attempts without mixing evidence across clean-reference generations and fails closed on ambiguous/malformed lineage instead of guessing attempt order.

Local schema-independent regression: `37 passed`. No shared contract is modified.
