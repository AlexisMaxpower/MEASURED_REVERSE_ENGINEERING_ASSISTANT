# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 14 durable revision comparison implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 14: **direct user instruction**  
Рабочая ветка: `chat-5/pass-14`  
Центральный baseline Pass 14: `main` @ `d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`

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
→ durable revision comparison
→ local/internal GET-only HTTP transport
→ optional authenticated HTTP cursor boundary
```

## Актуальная orchestration truth

Round 13 закрыт и интегрирован центральным оркестратором. Pass 14 начат непосредственно от актуального `main` @ `d6758d3a...`; исторические worker branches не использовались как implementation baseline.

Pass 14 изменяет только `chat_5_lifecycle_engineering_knowledge/`. Shared contracts, canonical fixtures, Chat 1–4, workflows и SQLite schema не меняются.

## Реализовано

### Lifecycle / persistence

- Revision / Manufacturing / Installation / Test / Failure domain;
- PhysicalPartInstance identity/state machine;
- exact failure/evidence linkage;
- lifecycle repository + unit of work;
- authoritative SQLite snapshot;
- normalized relational read model;
- backup/restore and guarded read-only session.

### CAD → lifecycle truth

- canonical numerical CAD verification отделена от runtime evidence;
- runtime `VERIFIED | FAILED | UNVERIFIED` сохраняется через persistence/read model;
- runtime-gated manufacturing eligibility fail-closed;
- numerical VERIFIED не повышает runtime UNVERIFIED до VERIFIED.

### Engineering knowledge

- revision lineage/outcomes;
- durable revision comparison;
- equipment/position history;
- exact failure-pattern groups;
- replacement chains;
- snapshot/query-bound pagination;
- materialized revision/failure aggregates;
- GET-only WSGI read transport;
- optional HMAC-SHA256 cursor authentication.

### Pass 14 — durable revision comparison

Исторический `RevisionComparison` существовал только как in-memory projection. Pass 14 переносит ту же factual semantics на committed SQLite read model без новой предметной логики.

`SQLiteLifecycleReadOnlySession.knowledge.compare_revisions(left_revision_id, right_revision_id)` возвращает существующий `RevisionComparisonResult`:

- revision IDs;
- distinct sorted manufacturing materials;
- exact failure count;
- exact test count;
- revision-level lifecycle state по исторической deterministic projection semantics.

Обе ревизии должны существовать и принадлежать одному `part_id`. Missing/cross-part inputs fail closed.

Все SQL statements проходят через Pass-13 snapshot guard. Если committed generation меняется во время long-lived session, comparison не смешивает поколения: возникает `LifecycleReadOnlyStaleError`, после чего требуется `refresh()`.

### HTTP boundary

Добавлен GET endpoint:

```text
/v1/knowledge/revision-comparison
  ?left_revision_id=<id>
  &right_revision_id=<id>
```

Он использует тот же read-only session/repository и существующую JSON serialization. Invalid/missing/cross-part inputs возвращаются как `400 invalid_request`. HTTP schema остаётся `mrea.lifecycle-http.v1`, потому что это additive GET route без изменения существующих payload contracts.

## Проверка Pass 14

Tested implementation SHA:

```text
8f5394c9ad2ffe1bfefc02021b78a9c7a17320d0
```

MREA CI:

```text
36811581113 — SUCCESS
Chat 5 / Lifecycle: SUCCESS
Contracts / canonical fixtures: SUCCESS
Chat 4 / Generic CAD gate: SUCCESS
Integration / Chat 4 -> Chat 5: SUCCESS
```

## Documentation

- `docs/PASS_14_DURABLE_REVISION_COMPARISON.md`
- `docs/BUILD_REUSE_CHECK_PASS14_REVISION_COMPARISON.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–13 docs remain authoritative for their slices.

## Still intentionally out of scope

- ranking revisions or recommending a preferred revision;
- causal/semantic interpretation of failures or tests;
- client authentication/authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
