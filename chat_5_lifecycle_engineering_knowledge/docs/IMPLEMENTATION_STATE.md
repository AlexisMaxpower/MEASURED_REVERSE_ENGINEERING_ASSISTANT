# Chat 5 — Implementation State

## Snapshot

- Date: **2026-10-02**
- Branch: `chat-5/pass-18`
- Slice: **Lifecycle & Engineering Knowledge**
- Authorization: **direct user instruction — Pass 18**
- Orchestration directive: `OD-2026-10-02-010`
- Shared baseline at worker start: `main` @ `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`
- Tested implementation SHA: `74c0c32fa2d7195818d651b51645cd52e8777914`
- MREA CI: `36946371201` — **SUCCESS**
- Chat 5 / Lifecycle: **93 passed in 5.23s**
- Contracts / canonical fixtures: **SUCCESS**
- Chat 4 / Generic CAD gate: **SUCCESS**
- Integration / Chat 4 -> Chat 5: **SUCCESS**
- State: **Pass 18 implementation verified; final handoff/freeze pending**

## Baseline discipline

Round 17 was closed and integrated before Pass 18 started. The worker branch was created directly from the then-current shared `main` @ `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`, as required by `OD-2026-10-02-010`.

No historical Pass-17 worker or integration branch was used as the implementation base.

No files outside `chat_5_lifecycle_engineering_knowledge/` are changed by Pass 18.

## Gap closed

The Chat 5 role explicitly owns `field status`. Before Pass 18, durable physical history and equipment occupancy existed, but consumers had to inspect the whole physical timeline to determine the current state of one exact manufactured instance.

Pass 18 adds a deterministic, source-backed current field-status projection over that already committed physical timeline.

## Delivered surface

`mrea_lifecycle.field_status` provides:

- `PhysicalFieldStatus`;
- `PhysicalTimelineQuery`;
- `build_physical_field_status(...)`;
- `get_physical_field_status(...)`.

The package root exports all four symbols.

`get_physical_field_status(session.queries, instance_id)` performs one snapshot-guarded `physical_timeline(...)` read and derives current state only from the latest persisted physical event.

## Returned facts

The projection preserves:

- physical `instance_id`;
- exact `revision_id` and `manufacturing_id` identity;
- current `PhysicalPartState`;
- exact state-change timestamp;
- exact latest source event ID and sequence;
- latest persisted installation/test/failure linkage;
- latest persisted equipment/position context;
- exact latest-event test outcome, replacement instance and notes when present.

`ACTIVATED` maps to internal current state `ACTIVE`; every other supported physical event maps directly to its established `PhysicalPartState`.

No free-text parsing is used to infer state.

## Fail-closed integrity boundary

Before emitting status, the full returned timeline is checked for:

- stable instance identity;
- stable revision identity;
- stable manufacturing identity;
- strictly increasing sequence;
- non-decreasing event time;
- supported physical event vocabulary.

Contradiction raises `LifecycleKnowledgeIntegrityError`. Blank or missing instance IDs fail closed with `ValueError`.

The projection therefore does not silently choose a state from internally contradictory durable facts.

## Occupancy boundary

`equipment_id` and `position` are copied from the latest persisted physical event. They are evidence context, not a new occupancy inference.

The existing `equipment_occupancy(...)` query remains authoritative for current equipment/position occupancy, including the rule that `FAILED` still occupies its location until explicit removal.

## Non-inference boundary

Pass 18 does not:

- mutate lifecycle history;
- infer failures/tests that were not recorded;
- parse free text into engineering truth;
- infer causality;
- rank/recommend revisions;
- promote unverified CAD/runtime facts;
- synthesize geometry;
- add semantic search, embeddings or an LLM.

## Compatibility

Unchanged:

- `core/contracts/**` and canonical fixtures;
- SQLite relational and authoritative snapshot schemas;
- cursor formats/authentication;
- manufacturing eligibility;
- physical lifecycle transition semantics;
- existing HTTP routes and `mrea.lifecycle-http.v1`;
- Chat 1–4 code;
- workflow definitions.

## Pass 18 delta before freeze

- `README.md`;
- `docs/IMPLEMENTATION_STATE.md`;
- `docs/PASS_18_PHYSICAL_FIELD_STATUS.md`;
- `src/mrea_lifecycle/__init__.py`;
- `src/mrea_lifecycle/field_status.py`;
- `tests/test_field_status.py`.

`ORCHESTRATOR_HANDOFF.md` is the final worker mutation. After that commit the branch is frozen and exact-head CI is verified without another worker change.
