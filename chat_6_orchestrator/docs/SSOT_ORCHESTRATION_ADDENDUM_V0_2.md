# MREA SSOT — Orchestration Addendum v0.2

This addendum extends SSOT v0.1 with Chat 6.

## Chat 6
Chat 6 is the sole Orchestrator / Repository Integrator. It has repository access and coordinates Chat 1–5.

### Authority
Chat 6 owns canonical shared contracts, fixtures, integration policies, ownership boundaries, release gates and cross-slice decisions.

### Communication model
Each slice contains the same control filename:

`ORCHESTRATOR_DIRECTIVE.md`

The file is deliberately duplicated as a directive mailbox. Canonical facts are centralized in:
- `core/contracts/`
- `tests/fixtures/contracts/`
- `chat_6_orchestrator/ORCHESTRATION_STATE.md`

This avoids five drifting copies of shared truth.

### Required startup sequence for Chat 1–5
1. Read current repository state relevant to its slice.
2. Read product SSOT.
3. Read local `ORCHESTRATOR_DIRECTIVE.md`.
4. Read canonical upstream/downstream contracts.
5. Read canonical fixtures.
6. Only then change code.

### Contract change policy
A slice may design internal types freely, but a shared wire contract changes only through Chat 6 after impact analysis.
