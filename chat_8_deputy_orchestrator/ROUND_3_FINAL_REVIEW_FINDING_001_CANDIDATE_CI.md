# ROUND 3 — FINAL_REVIEW_FINDING 001

**Reviewer:** Chat 8 — Deputy Orchestrator 2 / Final Certifier  
**Owner:** Chat 6 — Primary Orchestrator / shared CI infrastructure  
**Severity:** BLOCKING / HIGH  
**Status:** OPEN  
**Detected:** 2026-09-30  
**Scope:** Round 3 Stage-2 integration-candidate CI readiness

## Problem

The current shared workflow `.github/workflows/ci.yml` cannot produce the protocol-required complete GitHub Actions evidence for `integration/pass-3-candidate`.

This is a shared CI infrastructure defect. It is not a worker-slice defect and must not be worked around inside Chat 1–5 code.

## Evidence

Current workflow trigger:

```yaml
on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main
      - "chat-*/pass-*"
```

A push to `integration/pass-3-candidate` therefore does not trigger MREA CI.

If Deputy 1 opens a PR from `integration/pass-3-candidate` to `main`, slice jobs execute, but the boundary conditions are inconsistent for an integration head:

- `Integration / Chat 1 -> Chat 2` runs only for `main`, Chat-1/Chat-2 PR heads, or Chat-1/Chat-2 push refs. An integration PR head is skipped.
- `Integration / Chat 2 -> Chat 3` runs for any pull request and therefore executes.
- `Integration / Chat 3 -> Chat 4` runs only for `main`, Chat-3/Chat-4 PR heads, or Chat-3/Chat-4 push refs. An integration PR head is skipped.
- `Integration / Chat 4 -> Chat 5` runs only for `main`, Chat-4/Chat-5 PR heads, or Chat-4/Chat-5 push refs. An integration PR head is skipped.

Consequently a candidate PR may appear broadly green while three of the four mandatory cross-slice gates are `skipped`.

## Protocol conflict

The Deputy Orchestrators Protocol requires Deputy 1 to create `integration/pass-N-candidate` and run full CI on that candidate before handoff to Chat 8.

Chat 8 must later verify candidate CI including:

- all slice tests;
- contracts;
- all four boundaries;
- golden path;
- skipped/cancelled job behavior.

The current workflow cannot satisfy the four-boundary portion for an integration candidate without changing shared CI or substituting weaker non-CI evidence.

## Risk

Without correction, Round 3 can reach Stage 3 with incomplete candidate evidence while appearing green at PR level. This specifically creates a false-negative risk for cross-slice regressions in:

```text
Chat 1 -> Chat 2
Chat 3 -> Chat 4
Chat 4 -> Chat 5
```

A local/manual test run is useful supporting evidence but is not equivalent to the protocol-required candidate CI evidence.

## Required correction

Chat 6 must make the minimal shared-CI correction before Round-3 candidate certification:

1. ensure MREA CI is triggerable on `integration/pass-*-candidate`;
2. ensure all four cross-slice boundary jobs execute for that candidate, not `skipped` solely because the head ref is `integration/...`;
3. preserve existing worker-branch behavior unless there is a documented reason to change it;
4. run and record a full green CI run for the corrected shared `main`;
5. hand the corrected current `main` to Deputy 1;
6. Deputy 1 must independently re-audit the CI change, build/rebase the candidate from the corrected current `main`, and obtain complete candidate CI evidence.

A suitable implementation may explicitly include `integration/pass-*-candidate` in workflow triggers and boundary conditions, or use a simpler condition that guarantees all four boundary jobs on integration-candidate PRs/pushes. The exact implementation remains owned by Chat 6.

## Non-scope

This finding does not change the previously verified Round-3 worker SHAs and does not alter the real-host truth gate:

```text
REAL_HOST = UNVERIFIED
EXTERNAL_GATE_UNVERIFIED
```

No worker branch should be reopened for this finding.

## Closure criteria

`FINAL_REVIEW_FINDING_001 = CLOSED` only after:

- the shared CI correction is present on `main`;
- corrected `main` CI is green;
- Deputy 1 re-audits the correction;
- `integration/pass-3-candidate` exists;
- candidate CI shows all four boundary jobs actually executed successfully (not skipped).

Until then, Chat 8 must not certify or merge the Round-3 candidate.
