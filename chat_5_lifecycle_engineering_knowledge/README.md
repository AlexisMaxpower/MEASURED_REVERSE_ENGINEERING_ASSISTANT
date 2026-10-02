# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 19 physical field-status HTTP transport implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 19: **direct user instruction**  
Рабочая ветка: `chat-5/pass-19`  
Центральный baseline Pass 19: `main` @ `701209f8a92c6e4ee6c89ea1a4a5ed4aa6e40f26`

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

Round 18 закрыт и интегрирован. Pass 19 начинается непосредственно от актуального closure baseline `main` @ `701209f8...` по `OD-2026-10-02-011`; исторические worker/integration branches не используются как implementation baseline.

Round-18 baseline уже включает финальное fail-closed усиление field-status projection: полную проверку vocabulary, legal transition replay, обязательный outcome для `TESTED` и activation только после persisted `TESTED/PASSED`.

Все изменения Pass 19 находятся внутри `chat_5_lifecycle_engineering_knowledge/`. Shared contracts, canonical fixtures, Chat 1–4, workflows и SQLite schema не меняются.

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

## Pass 18–19 field-status chain

### Pass 18 — durable physical field status

`get_physical_field_status(session.queries, instance_id)` builds one current physical state from the committed physical timeline. Before emitting a status it validates identity, sequence, chronology, event vocabulary and the accepted physical state-machine transitions. Contradictory durable data raises `LifecycleKnowledgeIntegrityError`.

Location fields are latest-event evidence, not an independent occupancy claim. Existing `equipment_occupancy(...)` remains the current equipment mapping authority.

### Pass 19 — GET-only transport completion

Top-level `build_read_only_lifecycle_http_app(...)` now returns an additive adapter exposing:

```text
GET /v1/lifecycle/physical-field-status?instance_id=<id>
```

The route performs exactly one guarded session read through the Pass-18 projection and serializes the existing `PhysicalFieldStatus`; it does not reconstruct state independently.

Fail-closed request behavior:

- missing/blank/unknown instance -> `400 invalid_request`;
- unexpected parameters -> `400 invalid_request`;
- non-GET method -> `405 method_not_allowed`;
- stale read model -> `409 read_model_stale`;
- durable timeline integrity contradiction -> `409 read_model_integrity_error`;
- unavailable read model -> `503 read_model_unavailable`.

All pre-existing routes delegate to the accepted base HTTP adapter unchanged. `LIFECYCLE_HTTP_API_SCHEMA_VERSION` remains `mrea.lifecycle-http.v1`.

## Documentation

- `docs/PASS_15_STRUCTURED_REVISION_COMPARISON.md`
- `docs/PASS_16_REVISION_CHANGE_EXPLANATION.md`
- `docs/PASS_17_REVISION_CHANGE_EXPLANATION_HTTP.md`
- `docs/PASS_18_PHYSICAL_FIELD_STATUS.md`
- `docs/PASS_19_PHYSICAL_FIELD_STATUS_HTTP.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–14 docs remain authoritative for their slices.

## Still intentionally out of scope

- geometry comparison without approved upstream durable facts;
- revision ranking/recommendation;
- causal/semantic/AI interpretation beyond deterministic stored-fact projection;
- client authn/authz and deployment edge policy;
- field-device synchronization;
- shared contract expansion for physical-only events.
