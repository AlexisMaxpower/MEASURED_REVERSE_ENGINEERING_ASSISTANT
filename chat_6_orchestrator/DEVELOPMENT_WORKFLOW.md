# MREA Development Workflow — Pass 2+

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Effective from:** Pass 2

## Goal

Prevent worker-chat experiments or integration defects from landing directly in `main` before orchestration review.

## Branch model

`main` is the accepted integration baseline.

Each worker chat develops the next pass in its own branch:

- Chat 1: `chat-1/pass-2`
- Chat 2: `chat-2/pass-2`
- Chat 3: `chat-3/pass-2`
- Chat 4: `chat-4/pass-2`
- Chat 5: `chat-5/pass-2`

For later passes use the same pattern: `chat-N/pass-X`.

## Start of a pass

1. Chat 6 reviews current `main`.
2. Chat 6 publishes a new `ORCHESTRATOR_DIRECTIVE.md` revision.
3. Worker branch is created from the accepted `main` baseline.
4. Worker reads:
   - its `ORCHESTRATOR_DIRECTIVE.md`;
   - current canonical contracts/policies;
   - upstream fixtures/contracts;
   - its previous handoff/state.

## During implementation

Worker chat:

- changes only its owned slice unless directive explicitly allows otherwise;
- does not edit `core/contracts/` or canonical fixtures;
- does not commit pass implementation directly to `main`;
- records Build/Reuse decisions for non-trivial dependencies;
- preserves explicit uncertainty/conflicts instead of hiding them;
- raises a Change Request when a shared contract is insufficient.

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
9. tests not executed and why;
10. known limitations;
11. open Change Requests;
12. requested acceptance gate.

A worker response in chat is not the source of truth; repository handoff is.

## Chat 6 review

Chat 6 checks:

- branch diff against accepted `main`;
- ownership violations;
- canonical contract compatibility;
- upstream/downstream integration;
- tests and evidence;
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

## Round completion

A round is not green merely because all five worker slices report success.

Chat 6 must separately evaluate boundaries:

```text
Chat 1 → Chat 2
Chat 2 → Chat 3
Chat 3 → Chat 4
Chat 4 → Chat 5
```

Round state:

- `GREEN`: required slice gates and required cross-slice gates pass;
- `PARTIAL`: useful slice work accepted but at least one required integration gate is not green;
- `BLOCKED`: a shared blocker prevents meaningful progress.

## Shared-contract changes

Only Chat 6 owns canonical shared contracts.

Worker submits a Change Request; Chat 6 decides whether to:

- reject it as misuse of existing contract;
- accept backward-compatible amendment;
- introduce new version/migration.

No worker chat may solve integration friction by silently redefining a canonical contract locally.
