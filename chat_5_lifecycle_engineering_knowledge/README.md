# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Pass 13 read-only snapshot drift guard implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **repository/GitHub + MREA SSOT**  
Авторизация Pass 13: **direct user instruction**  
Рабочая ветка: `chat-5/pass-13`  
Центральный baseline Pass 13: `main` @ `4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`

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
→ local/internal read-only HTTP transport
→ optional authenticated HTTP cursor boundary
```

## Актуальная orchestration truth

Round 12 закрыт и принят центральным оркестратором в `main`. Pass 13 начат непосредственно от текущего общего baseline `4edde5c...`; исторические worker branches не использовались как implementation baseline.

Pass 13 не меняет shared contracts, Chat 1–4, root integration tests, workflows или SQLite schema.

## Реализовано

### Lifecycle / persistence

- Revision / Manufacturing / Installation / Test / Failure domain;
- PhysicalPartInstance identity/state machine;
- exact failure/evidence linkage;
- lifecycle repository + unit of work;
- SQLite authoritative snapshot;
- normalized relational read model;
- backup/restore and read-only session.

### CAD → lifecycle truth

- canonical numerical CAD verification отделена от runtime evidence;
- runtime `VERIFIED | FAILED | UNVERIFIED` сохраняется через persistence/read model;
- runtime-gated manufacturing eligibility fail-closed;
- numerical VERIFIED не повышает runtime UNVERIFIED до VERIFIED.

### Engineering knowledge

- revision lineage/outcomes;
- equipment/position history;
- exact failure-pattern groups;
- replacement chains;
- snapshot/query-bound pagination;
- materialized revision/failure aggregates;
- GET-only WSGI read transport;
- optional HMAC-SHA256 cursor authentication.

### Pass 13 — read-only snapshot drift guard

До Pass 13 read-only session принимал snapshot version при открытии, но его SQLite connection работал в autocommit. Поэтому после внешнего writer commit тот же long-lived session мог прочитать более новые relational/materialized rows, продолжая сообщать старый `snapshot_version`.

Теперь repository SQL проходит через snapshot guard:

1. перед каждым statement проверяются authoritative snapshot version, read-model version и relational schema generation;
2. после `fetchone()` / `fetchall()` metadata проверяется повторно;
3. если generation изменилась, rows не принимаются и поднимается `LifecycleReadOnlyStaleError` с требованием `refresh()`;
4. `refresh()` закрывает старое соединение и явно принимает новую committed generation.

Guard намеренно не держит long-lived read transaction: завершённый read-only session не должен блокировать отдельного writer в default SQLite rollback-journal mode.

## Проверка Pass 13

Tested implementation SHA:

```text
a26c1d8f6927e3ebdfcf69d7f759893cd7b139bd
```

MREA CI:

```text
36806176020 — SUCCESS
Chat 5 / Lifecycle: 73 passed in 3.05s
Contracts / canonical fixtures: SUCCESS
Chat 4 / Generic CAD gate: SUCCESS
Integration / Chat 4 -> Chat 5: SUCCESS
```

## Documentation

- `docs/PASS_13_READ_ONLY_SNAPSHOT_DRIFT_GUARD.md`
- `docs/BUILD_REUSE_CHECK_PASS13_SNAPSHOT_GUARD.md`
- `docs/IMPLEMENTATION_STATE.md`
- historical Pass 3–12 docs remain authoritative for their slices.

## Still intentionally out of scope

- client authentication/authorization;
- TLS / reverse-proxy / CORS / rate-limiting policy;
- secret provisioning/storage policy;
- framework-specific application shell;
- AI / semantic interpretation;
- field-device synchronization;
- shared contract expansion for physical-only events.
