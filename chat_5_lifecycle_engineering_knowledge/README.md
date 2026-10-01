# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 15 structured revision comparison details implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 15: **direct user instruction**  
Рабочая ветка: `chat-5/pass-15`  
Центральный baseline Pass 15: `main` @ `99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

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
→ local/internal GET-only HTTP transport
```

## Актуальная orchestration truth

Round 14 закрыт и интегрирован. Pass 15 начат непосредственно от актуального closure baseline `main` @ `99d8c6d9...`; старые worker branches не использовались как implementation baseline.

Все изменения Pass 15 находятся внутри `chat_5_lifecycle_engineering_knowledge/`. Shared contracts, canonical fixtures, Chat 1–4, workflows и SQLite schema не меняются.

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
- equipment/position history;
- failure-pattern groups;
- replacement chains;
- snapshot-bound pagination/materialized aggregates;
- GET-only WSGI transport with optional authenticated cursors.

## Pass 15 — structured revision comparison details

Pass 14 восстановил durable comparison, но его результат был намеренно компактным: материалы, counts и lifecycle state. Pass 15 добавляет отдельный additive factual snapshot для инженерного side-by-side review.

`SQLiteLifecycleReadOnlySession.knowledge.compare_revision_details(left_revision_id, right_revision_id)` возвращает для каждой стороны только уже сохранённые Chat-5 facts:

- revision metadata: code, created time, parent, origin, notes, source CAD artifact;
- persisted CAD verification/runtime status fields when they exist;
- manufacturing records: material, method, batch, machine, print profile, contractor, cost, post-processing;
- tests with exact artifact IDs;
- failures with exact evidence IDs and stored cause/feature fields;
- deterministic revision-level lifecycle state.

Результат содержит deterministic `changed_categories`, но не содержит ranking, score, recommendation или causal inference.

Geometry намеренно не синтезируется: текущая durable Chat-5 schema не содержит утверждённого upstream geometry comparison payload. Геометрия может появиться здесь только после явного approved contract/read-model source, а не через локальную догадку.

### HTTP boundary

Добавлен additive GET endpoint:

```text
/v1/knowledge/revision-comparison-details
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

Он использует существующий guarded read-only session. Missing/cross-part/unexpected inputs fail closed как `400 invalid_request`. `mrea.lifecycle-http.v1` не меняется: существующие routes/payloads не изменены.

## Проверка Pass 15 implementation

Tested implementation SHA:

```text
a0372ac3e7e4036a1b17d600cc3c29b3d09bb5a4
```

MREA CI:

```text
36816060128 — SUCCESS
Chat 5 / Lifecycle: 82 passed in 3.54s
Contracts / canonical fixtures: SUCCESS
Chat 4 / Generic CAD gate: SUCCESS
Integration / Chat 4 -> Chat 5: SUCCESS
```

## Documentation

- `docs/PASS_15_STRUCTURED_REVISION_COMPARISON.md`
- `docs/BUILD_REUSE_CHECK_PASS15_REVISION_COMPARISON.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–14 docs remain authoritative for their slices.

## Still intentionally out of scope

- geometry comparison without approved upstream durable facts;
- revision ranking/recommendation;
- causal/semantic/AI interpretation;
- client authn/authz and deployment edge policy;
- field-device synchronization;
- shared contract expansion for physical-only events.
