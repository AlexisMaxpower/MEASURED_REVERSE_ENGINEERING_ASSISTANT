# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 17 revision-change explanation HTTP implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 17: **direct user instruction**  
Рабочая ветка: `chat-5/pass-17`  
Центральный baseline Pass 17: `main` @ `933d925c69944d40859ae1f9ff80d7a3ecb7f760`

## Назначение области

Chat 5 ведёт инженерную историю ревизии и фактическую жизнь конкретного изготовленного экземпляра:

```text
Revision
→ ManufacturingRecord
→ PhysicalPartInstance
→ Installed / Tested / Active
→ Failed / Removed / Superseded
→ deterministic engineering knowledge queries
→ snapshot-bound keyset pagination
→ materialized analytical read model
→ guarded read-only query session
→ compact + structured revision comparison
→ source-backed revision-change explanation
→ local/internal GET-only HTTP transport
```

## Актуальная orchestration truth

Round 16 закрыт и интегрирован. Pass 17 начинается непосредственно от актуального closure baseline `main` @ `933d925c...`; исторические worker/integration branches не используются как implementation baseline.

Все изменения Pass 17 находятся внутри `chat_5_lifecycle_engineering_knowledge/`. Shared contracts, canonical fixtures, Chat 1–4, workflows и SQLite schema не меняются.

## Реализовано

### Lifecycle / persistence

- revision/manufacturing/installation/test/failure domain;
- physical instance lifecycle and deterministic state machine;
- exact test/failure/evidence linkage;
- authoritative SQLite snapshot + normalized relational read model;
- backup/restore;
- snapshot-drift guarded read-only sessions.

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

The result has deterministic `changed_categories` and intentionally omits ranking, recommendation, causal inference and fabricated geometry.

### Pass 16 — source-backed revision-change explanation

`explain_revision_changes(...)` converts one guarded structured comparison into ordered factual deltas. Every delta preserves exact source revision IDs and, where applicable, exact manufacturing/test/failure record IDs and exact stored artifact/evidence IDs.

The explanation verifies that emitted category order exactly matches the underlying durable comparison. It does not perform a second independent read, rank revisions or infer why a result occurred.

### Pass 17 — HTTP transport completion

Added additive GET endpoint:

```text
/v1/knowledge/revision-change-explanation
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

The route delegates directly to the Pass-16 explanation inside the existing guarded read-only session and existing deterministic JSON serializer.

Fail-closed request behavior is preserved:

- missing/blank parameters -> `400 invalid_request`;
- cross-part or missing revisions -> `400 invalid_request`;
- unexpected parameters -> `400 invalid_request`;
- non-GET methods -> `405 method_not_allowed`;
- stale/unavailable read model -> existing `409/503` boundaries.

`LIFECYCLE_HTTP_API_SCHEMA_VERSION` remains `mrea.lifecycle-http.v1`; existing routes and payloads are unchanged.

## Documentation

- `docs/PASS_15_STRUCTURED_REVISION_COMPARISON.md`
- `docs/PASS_16_REVISION_CHANGE_EXPLANATION.md`
- `docs/PASS_17_REVISION_CHANGE_EXPLANATION_HTTP.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–14 docs remain authoritative for their slices.

## Still intentionally out of scope

- geometry comparison without approved upstream durable facts;
- revision ranking/recommendation;
- causal/semantic/AI interpretation beyond deterministic stored-fact projection;
- client authn/authz and deployment edge policy;
- field-device synchronization;
- shared contract expansion for physical-only events.
