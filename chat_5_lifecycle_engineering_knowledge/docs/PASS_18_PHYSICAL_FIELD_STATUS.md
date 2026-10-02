# Pass 18 — Durable Physical Field Status

## Purpose

Pass 18 closes the explicit `field status` gap from the Chat 5 role without adding a new shared contract, schema migration, AI layer or independent truth source.

The existing durable physical timeline already contains the authoritative committed history for one manufactured instance. Pass 18 adds a deterministic projection over that history:

```text
committed physical timeline
→ validate identity/order/event vocabulary/state-machine history
→ select latest persisted physical event
→ map event type to PhysicalPartState
→ return exact source-event linkage
```

## Public Python surface

`mrea_lifecycle.field_status` adds:

- `PhysicalFieldStatus`;
- `PhysicalTimelineQuery`;
- `build_physical_field_status(...)`;
- `get_physical_field_status(...)`.

The package root exports these symbols.

`get_physical_field_status(session.queries, instance_id)` reads exactly one snapshot-guarded physical timeline through the existing `SQLiteLifecycleReadOnlySession` query repository and projects the current state from its latest committed event.

## Returned facts

`PhysicalFieldStatus` contains:

- `instance_id`;
- `revision_id`;
- `manufacturing_id`;
- current `PhysicalPartState`;
- `state_changed_at`;
- exact `source_event_id` and `source_event_sequence`;
- latest event linkage to installation/test/failure where present;
- latest persisted `equipment_id` and `position` where present;
- persisted physical test outcome when it belongs to the latest event;
- exact replacement instance ID when present;
- exact latest-event notes when present.

The location fields are copied from the latest persisted event. They are evidence context, not a separate occupancy claim. Current equipment occupancy remains owned by the existing `equipment_occupancy(...)` projection.

## State mapping

The projection reuses the established physical lifecycle semantics:

```text
MANUFACTURED -> MANUFACTURED
INSTALLED    -> INSTALLED
TESTED       -> TESTED
ACTIVATED    -> ACTIVE
FAILED       -> FAILED
REMOVED      -> REMOVED
SUPERSEDED   -> SUPERSEDED
```

No free-text test/failure field is parsed to derive state.

## Fail-closed integrity checks

Before emitting status, the complete returned timeline is checked for:

- one stable `instance_id`;
- one stable `revision_id`;
- one stable `manufacturing_id`;
- strictly increasing persisted sequence;
- non-decreasing event time;
- supported physical lifecycle event type;
- `MANUFACTURED` as the first physical event;
- only transitions that the existing `PhysicalPartLifecycleService` can produce;
- an explicit `PASSED` or `FAILED` outcome on every `TESTED` event;
- `ACTIVATED` only immediately after a `TESTED` event whose persisted outcome is `PASSED`.

Identity/order/vocabulary/state-machine divergence raises `LifecycleKnowledgeIntegrityError` rather than returning a plausible status from corrupt durable history.

Blank or unknown instance IDs fail closed with `ValueError`.

The single-instance projection can validate the superseded instance's own transition into `SUPERSEDED`; cross-instance replacement eligibility remains owned by the authoritative lifecycle service because that rule depends on the replacement instance's separate timeline and equipment position.

## Truth boundary

Pass 18 does not:

- mutate lifecycle history;
- infer causality;
- infer a missing failure or test;
- reinterpret free text;
- promote CAD/runtime verification;
- rank/recommend revisions;
- synthesize geometry;
- add semantic search or an LLM.

The status is only a projection of already committed Chat 5 physical facts.

## Compatibility

Unchanged:

- `core/contracts/**`;
- canonical fixtures;
- SQLite snapshot/relational schemas;
- manufacturing eligibility;
- physical transition rules;
- cursor formats;
- existing HTTP routes/schema;
- Chat 1–4 code;
- workflows.

HTTP exposure is intentionally not added in this pass. This pass establishes and tests the internal durable field-status contract first, mirroring the earlier revision-explanation pattern where transport was added only after the factual projection was stable.
