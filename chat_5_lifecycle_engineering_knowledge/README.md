# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 18 durable physical field-status projection implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 18: **direct user instruction**  
Рабочая ветка: `chat-5/pass-18`  
Центральный baseline Pass 18: `main` @ `af4bf4ce9e3c5da0f8e6ecdc185425b5985e4223`

## Назначение области

Chat 5 ведёт инженерную историю ревизии и фактическую жизнь конкретного изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed / Tested / Active
→ Failed / Removed / Superseded
→ deterministic current field status
→ deterministic engineering knowledge queries
→ snapshot-bound keyset pagination
→ materialized analytical read model
→ guarded read-only query session
→ compact + structured revision comparison
→ source-backed revision-change explanation
→ local/internal GET-only HTTP transport
```

## Актуальная orchestration truth

Round 17 закрыт и интегрирован. Pass 18 начинается непосредственно от актуального closure baseline `main` @ `af4bf4ce...`; исторические worker/integration branches не используются как implementation baseline.

Все изменения Pass 18 находятся внутри `chat_5_lifecycle_engineering_knowledge/`. Shared contracts, canonical fixtures, Chat 1–4, workflows и SQLite schema не меняются.

## Реализовано

### Lifecycle / persistence

- revision/manufacturing/installation/test/failure domain;
- physical instance lifecycle and deterministic state machine;
- exact test/failure/evidence linkage;
- authoritative SQLite snapshot + normalized relational read model;
- backup/restore;
- snapshot-drift guarded read-only sessions;
- deterministic current field-status projection for one physical instance.

### CAD → lifecycle truth

- numerical verification отделена от runtime evidence;
- runtime `VERIFIED | FAILED | UNVERIFIED` сохраняется как факт;
- manufacturing eligibility fail-closed;
- knowledge/read surfaces не повышают unverified runtime truth.

### Engineering knowledge

- revision lineage/outcomes;
- compact durable revision comparison;
- structured factual revision comparison;
- deterministic source-backed revision-change explanation;
- equipment/position history;
- failure-pattern groups;
- replacement chains;
- snapshot-bound pagination/materialized aggregates;
- GET-only WSGI transport with optional authenticated cursors.

## Pass 15–17 revision knowledge chain

### Pass 15 — structured revision comparison

`SQLiteLifecycleReadOnlySession.knowledge.compare_revision_details(left_revision_id, right_revision_id)` exposes committed metadata, CAD truth fields, manufacturing records, tests, failures, exact artifact/evidence IDs and deterministic lifecycle state for both revisions.

### Pass 16 — source-backed revision-change explanation

`explain_revision_changes(...)` converts one guarded structured comparison into ordered factual deltas with exact source records/artifacts and without ranking, recommendation or causal inference.

### Pass 17 — HTTP transport completion

`GET /v1/knowledge/revision-change-explanation` exposes the same Pass-16 explanation through the guarded read-only HTTP adapter without duplicating comparison semantics.

## Pass 18 — durable physical field status

`get_physical_field_status(session.queries, instance_id)` builds one current physical state from the already persisted physical timeline.

The result preserves:

- exact physical instance, revision and manufacturing identity;
- current `PhysicalPartState`;
- exact timestamp and event ID/sequence that established that state;
- latest persisted installation/test/failure linkage;
- latest persisted equipment/position context;
- exact replacement/notes/test-outcome fields when they belong to the latest event.

Before emitting a status, the projection verifies stable instance/revision/manufacturing identity, strictly increasing sequence, non-decreasing time and supported event vocabulary. Contradictory durable data fails closed with `LifecycleKnowledgeIntegrityError`.

Location fields are latest-event evidence, not an independent occupancy claim. Existing `equipment_occupancy(...)` remains the current equipment mapping authority.

Pass 18 is deliberately Python/read-model only. HTTP exposure is deferred until the factual field-status projection has been independently integrated, following the same projection-first/transport-second pattern used by Pass 16–17.

## Documentation

- `docs/PASS_15_STRUCTURED_REVISION_COMPARISON.md`
- `docs/PASS_16_REVISION_CHANGE_EXPLANATION.md`
- `docs/PASS_17_REVISION_CHANGE_EXPLANATION_HTTP.md`
- `docs/PASS_18_PHYSICAL_FIELD_STATUS.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–14 docs remain authoritative for their slices.

## Still intentionally out of scope

- geometry comparison without approved upstream durable facts;
- revision ranking/recommendation;
- causal/semantic/AI interpretation beyond deterministic stored-fact projection;
- client authn/authz and deployment edge policy;
- field-device synchronization;
- shared contract expansion for physical-only events.
