# MREA — Round 4 Worker Intake

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Directive:** `OD-2026-09-30-004`  
**Date:** 2026-09-30  
**Status:** `WORKER_INTAKE_ACTIVE`

## Accepted central baseline

- pre-Round-4 planning baseline `main`: `bffc1dec2fe63c12b69a50c4bf348ef7df4cf662`;
- accepted tree: `435dda140d3980256ca32c42bd07d81b15c4328c`;
- Round-3 post-merge CI: `36651010221` — `SUCCESS`;
- Round-3 golden path: `SUCCESS`.

This intake records later worker development observed after Round 3. It is not an acceptance verdict by itself.

## Intake matrix

| Slice | Selected/target branch | Observed head | Handoff/freeze status | Round-4 Stage-1 state |
|---|---|---|---|---|
| Chat 1 | `chat-1/pass-4` | `beed09508c8cba294b1e78d7b6b7f3226f72d734` | stale Pass-3 handoff | `HANDOFF_REQUIRED` |
| Chat 2 | `chat-2/pass-6` | `539d58567046fd29ccf2d42b629227ffe8da6546` | Pass-6 handoff present/frozen | `SELECTED_FOR_REVIEW` |
| Chat 3 | `chat-3/pass-8` | `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49` | Pass-8 handoff present/frozen | `SELECTED_FOR_REVIEW_WITH_BASELINE_DRIFT` |
| Chat 4 | `chat-4/pass-7` | `d9633e3b8e95158d359e502e9797d4876384cd09` | stale Pass-3 handoff | `HANDOFF_REQUIRED` |
| Chat 5 | `chat-5/pass-8` | `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` | Pass-8 handoff present/frozen | `SELECTED_FOR_REVIEW` |

## Chat 1 intake

Observed later implementation adds clean-reference recapture lineage and source/supersession relationships.

The branch cannot enter Stage 1 as a frozen worker result until its handoff truthfully names Pass 4, the current implementation SHA, required CI evidence, delivered scope, known limitations and freeze state.

Chat 1 must not expand scope during handoff repair unless a concrete defect prevents a truthful handoff.

## Chat 2 intake

The selected Pass-6 cumulative cut includes:

1. Pass 4 measurement-type semantics (`mm` vs `deg`);
2. Pass 5 unit-neutral uncertainty;
3. Pass 6 canonical 1..3 anchor cardinality.

Chat 6 will review the cumulative slice delta, not treat each worker pass as a separate central round.

Worker history is not merged wholesale. Central integration will preserve current shared baseline and replay only accepted Chat-2-owned changes.

## Chat 3 intake

The selected Pass-8 cumulative cut includes later geometry/constraint work through deterministic residual-aware confidence.

Known baseline drift is already explicit in the handoff: old branch ancestry contains the obsolete shared integration lookup `cad_verification_report["dimensions"]`; current accepted main uses canonical `items`.

That stale shared file is not part of the accepted worker delta. Central replay must use current-main shared integration tests.

## Chat 4 intake

Observed later work includes broader SOLIDWORKS vendor capabilities, including ANGLE dimensions.

The current branch handoff still describes Pass 3. Therefore Stage 1 must wait for a new Pass-7 handoff/freeze.

Mandatory truth status remains:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

unless controlled Windows/SOLIDWORKS evidence is supplied.

## Chat 5 intake

The selected Pass-8 cumulative cut includes lifecycle persistence/read-only/engineering-knowledge evolution through snapshot-bound deterministic pagination.

The branch is frozen by its Pass-8 handoff. Chat 6 must verify that later read models remain derived from committed factual lifecycle state and do not reinterpret eligibility/failure facts into unsupported conclusions.

## Central replay exclusions

The following are never imported merely because they occur in worker ancestry:

- `.github/workflows/**`;
- `core/contracts/**`;
- canonical fixtures;
- Chat-6-owned shared integration tests;
- another slice's files;
- stale `ORCHESTRATOR_DIRECTIVE.md` copies.

Every accepted replay must preserve exact provenance back to its selected worker commit/blob.

## Intake verdict

```text
CHAT_1 = HANDOFF_REQUIRED
CHAT_2 = SELECTED_FOR_STAGE1_REVIEW
CHAT_3 = SELECTED_FOR_STAGE1_REVIEW_WITH_SHARED_BASELINE_DRIFT
CHAT_4 = HANDOFF_REQUIRED
CHAT_5 = SELECTED_FOR_STAGE1_REVIEW
ROUND_4_STAGE1_COMPLETE = FALSE
INTEGRATION_PASS_4_CANDIDATE_AUTHORIZED = FALSE
```
