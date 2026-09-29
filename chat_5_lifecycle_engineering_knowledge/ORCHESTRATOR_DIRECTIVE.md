# ORCHESTRATOR DIRECTIVE — Chat 5
**Revision:** OD-2026-09-29-001  
**Owner:** Chat 6

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/lifecycle_event_v1.json`

## Current directive
Existing lifecycle domain remains valid internal state. Add an outward adapter for canonical `LifecycleEvent v1`.

Rich Revision/Manufacturing/Installation/Test/Failure models remain internal; the shared event contract is intentionally thin in v1.

## Next acceptance target
REVISION_CREATED → MANUFACTURED → INSTALLED → FAILED → next revision can emit ordered canonical lifecycle events without losing internal evidence references.

## Do not
- promote internal enums/classes into repository-wide shared types;
- add AI before structured lifecycle data is stable;
- edit shared contracts directly.
