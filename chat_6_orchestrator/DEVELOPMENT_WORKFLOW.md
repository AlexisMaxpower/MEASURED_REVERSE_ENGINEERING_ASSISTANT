# MREA Development Workflow — Pass 2+

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Effective from:** Pass 2  
**Pass 3 amendment:** handoff branch freeze + shared-infrastructure-before-branch rule

## Goal

Prevent worker-chat experiments or integration defects from landing directly in `main` before orchestration review.

## Branch model

`main` is the accepted integration baseline.

Each worker chat develops the next pass in its own branch:

- Chat 1: `chat-1/pass-N`
- Chat 2: `chat-2/pass-N`
- Chat 3: `chat-3/pass-N`
- Chat 4: `chat-4/pass-N`
- Chat 5: `chat-5/pass-N`

All five branches for a pass MUST be created from the same accepted `main` SHA.

## Before branch creation

Chat 6 MUST first land all shared changes required for the pass on `main`:

- canonical contracts/policies;
- shared fixtures/integration tests;
- GitHub Actions changes;
- ADRs;
- orchestration documents;
- `ORCHESTRATOR_DIRECTIVE.md` updates.

Only after that shared baseline is complete does Chat 6 create the five worker branches.

This avoids the Pass 2 problem where CI/shared files were introduced after worker branches had already diverged.

## Start of a pass

1. Chat 6 reviews current `main`.
2. Chat 6 publishes a new directive revision.
3. Chat 6 completes shared/CI/integration infrastructure for the pass.
4. Chat 6 records the exact accepted `main` SHA.
5. Chat 6 creates all five worker branches from that exact SHA.
6. Worker reads:
   - its `ORCHESTRATOR_DIRECTIVE.md`;
   - current canonical contracts/policies;
   - upstream fixtures/contracts;
   - its previous handoff/state.

## During implementation

Worker chat:

- changes only its owned slice unless directive explicitly allows otherwise;
- does not edit `core/contracts/`, canonical fixtures, Chat-6 docs or shared CI unless directive explicitly assigns such work;
- does not commit pass implementation directly to `main`;
- records Build/Reuse decisions for non-trivial dependencies;
- preserves explicit uncertainty/conflicts instead of hiding them;
- raises a Change Request when a shared contract is insufficient;
- pushes work to its `chat-N/pass-X` branch so GitHub Actions can execute independent CI.

## CI requirement

Canonical CI workflow:

`.github/workflows/ci.yml`

From Pass 2 onward, CI evidence is mandatory where a job is executable on GitHub-hosted runners.

A worker statement such as `13 passed` is useful local evidence but is not equivalent to independent CI evidence.

The required CI layers are:

1. canonical contract/fixture validation;
2. slice-local tests for Chats 1–5;
3. executable cross-slice integration tests;
4. full post-merge CI on accepted `main`.

A worker branch with a red required CI job cannot be accepted for integration until the failure is resolved or Chat 6 explicitly classifies it as an environment-only gate.

See `chat_6_orchestrator/CI_POLICY.md`.

## Handoff requirement

Every worker chat MUST finish a pass by creating/updating:

`ORCHESTRATOR_HANDOFF.md`

The handoff must contain:

1. pass/directive revision;
2. branch name;
3. final branch commit SHA;
4. delivered functionality;
5. canonical inputs/outputs used;
6. files/modules changed;
7. test inventory;
8. tests actually executed and exact result;
9. CI run/check status known at handoff time;
10. tests not executed and why;
11. known limitations;
12. open Change Requests;
13. requested acceptance gate.

A worker response in chat is not the source of truth; repository handoff is.

## Handoff freezes the branch

**Publishing `ORCHESTRATOR_HANDOFF.md` freezes the worker branch.**

After handoff:

- worker MUST NOT push code changes;
- worker MUST NOT push documentation-only changes;
- worker MUST NOT move the branch head merely to record a later CI result;
- worker waits for Chat 6 verdict.

Chat 6 records post-handoff CI/review evidence centrally.

If Chat 6 returns `FIX_REQUIRED`, the branch is explicitly reopened for only the requested correction. The worker then updates handoff again and freezes the branch again.

## Review stability

Once Chat 6 starts review of a pass:

- shared contracts/CI/integration infrastructure on `main` should remain stable;
- Chat 6 must not casually move the integration baseline while worker PRs are under review;
- if an emergency shared change is necessary, affected PR reviews are explicitly restarted against the new baseline.

## Chat 6 review

Chat 6 checks:

- branch diff against accepted `main`;
- ownership violations;
- canonical contract compatibility;
- upstream/downstream integration;
- local tests and GitHub Actions evidence;
- duplicated functionality;
- shared invariants;
- Change Requests;
- documentation/handoff completeness.

Possible verdicts:

- `ACCEPTED`;
- `ACCEPTED_WITH_FOLLOWUP`;
- `FIX_REQUIRED`;
- `BLOCKED`;
- `REJECTED`.

Only accepted changes are integrated into `main`.

## Integration order

Chat 6 may choose merge order based on dependencies rather than chat number.

For each accepted merge:

1. verify PR-level CI on the relevant merge candidate;
2. merge accepted slice;
3. use the new `main` as the next dependency baseline;
4. require full final `main` CI before declaring the round green.

## Round completion

A round is not green merely because all five worker slices report success.

Chat 6 must separately evaluate relevant boundaries, including as implemented:

```text
Chat 1 -> Chat 2
Chat 2 -> Chat 3
Chat 3 -> Chat 4
Chat 4 -> Chat 5
```

Round state:

- `GREEN`: required slice gates, required CI jobs and required cross-slice gates pass on final assembled `main`;
- `PARTIAL`: useful slice work accepted but at least one required integration gate is not green;
- `BLOCKED`: a shared blocker prevents meaningful progress.

## Shared-contract changes

Only Chat 6 owns canonical shared contracts.

Worker submits a Change Request; Chat 6 decides whether to:

- reject it as misuse of existing contract;
- accept backward-compatible amendment;
- introduce new version/migration.

No worker chat may solve integration friction by silently redefining a canonical contract locally.
