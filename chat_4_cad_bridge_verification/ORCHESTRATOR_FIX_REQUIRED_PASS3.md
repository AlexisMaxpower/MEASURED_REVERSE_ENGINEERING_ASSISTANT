# ORCHESTRATOR FIX REQUIRED — Chat 4 Pass 3

**Owner:** Chat 6 — Primary Orchestrator  
**Status:** `FIX_REQUIRED`  
**Primary branch:** `chat-4/pass-3`  
**Side branch:** `chat-4b/pass-3`

## What is already preserved in GitHub

Primary Chat 4 work is present remotely at head `8e5c6c503f9bf7f7420b8f6b99d71797d3073d38` and includes the fail-closed runtime-evidence/readiness layer, tests and documentation.

## Blocking issue

Pass 3 is not formally complete:

1. `chat-4/pass-3` still contains the Pass-2 `ORCHESTRATOR_HANDOFF.md`; there is no final Pass-3 primary handoff.
2. `chat-4b/pass-3` contains only task/setup commits and does not contain the required `SOLIDWORKS_SIDE_HANDOFF.md` or the assigned host-readiness implementation.
3. The previous Chat 3 -> Chat 4 CI failure was caused by a Chat-6-owned integration-test defect (`dimensions` instead of canonical `items`). Chat 6 corrected this on `main` at `1a54ef40f84119d7482d971deb1e58749bf657b0`; do not work around it inside Chat 4.

## Required correction

1. Complete the assigned Side Chat 4B host-readiness implementation on `chat-4b/pass-3`.
2. Publish `chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md` on the side branch with exact final SHA, changed files, checks, tests/build status, exit codes and real-host status.
3. Integrate/reconcile the side result into `chat-4/pass-3` without changing canonical contracts or Chat-6-owned CI.
4. Run Chat 4 regression and relevant boundaries against the corrected current shared baseline.
5. Replace/update `chat_4_cad_bridge_verification/ORCHESTRATOR_HANDOFF.md` with a genuine **Pass 3** final handoff.
6. Freeze the primary branch after that handoff.

## Real-host truth rule

If no actual Windows 11 + SOLIDWORKS 2026 execution has occurred, the real-host status must remain `UNVERIFIED`. Do not simulate or infer success.

## Acceptance target

Only after the side implementation exists remotely, the side handoff exists remotely, the primary Pass-3 handoff exists remotely and required CI is green can Chat 4 become `PROVISIONALLY_ACCEPTED` for Deputy 1 review.
