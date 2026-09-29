# Chat 5 — Phase 2: Canonical LifecycleEvent Adapter

## Статус

- Date: **2026-09-29**
- Orchestrator directive: **OD-2026-09-29-001**
- Status: **implemented / locally verified**
- Shared contracts modified: **NO**

## 1. Основание

Chat 6 зафиксировал canonical inputs:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/lifecycle_event_v1.json`.

Directive требует сохранить богатую lifecycle domain model Chat 5 внутренней и добавить outward adapter к `LifecycleEvent v1`.

## 2. Архитектурное решение

```text
Revision / ManufacturingRecord / Installation / TestRecord / FailureRecord
                              ↓
                    internal LifecycleEvent
                              ↓
              CanonicalLifecycleEventAdapter
                              ↓
                 mrea.lifecycle-event.v1
```

`LifecycleState` остаётся внутренней derived projection.

Shared contract остаётся тонким и не импортирует internal enums/classes Chat 5.

## 3. Canonical output

Adapter выдаёт только поля shared `LifecycleEvent v1`:

```text
schema_version
event_id
event_type
occurred_at
sequence
revision_id
manufacturing_id
installation_id
test_id
failure_id
```

`schema_version` всегда:

```text
mrea.lifecycle-event.v1
```

Поддерживаемые event types берутся из текущего внутреннего Phase-1 vocabulary, которое contract test сверяет с Integrator-owned schema:

- `REVISION_CREATED`;
- `MANUFACTURED`;
- `INSTALLED`;
- `TESTED`;
- `FAILED`.

## 4. Boundary invariants

Adapter отклоняет:

- пустой `event_id`;
- пустой `revision_id`;
- `sequence < 1`;
- naive datetime без timezone;
- event type, отсутствующий в canonical vocabulary;
- `MANUFACTURED` без `manufacturing_id`;
- `INSTALLED` без `installation_id`;
- `TESTED` без `test_id`;
- `FAILED` без `failure_id`;
- duplicate `event_id` при batch export;
- duplicate `sequence` при batch export.

Timestamp нормализуется в UTC ISO-8601 (`Z`).

## 5. Ordering

Batch export сортирует internal events по `sequence`.

Таким образом порядок wire events не зависит от порядка iterable, переданного adapter-у.

Это обеспечивает deterministic canonical output для одинаковой внутренней истории.

## 6. Evidence policy

Canonical `LifecycleEvent v1` намеренно не содержит failure evidence payload.

Evidence не удаляется и не переносится в неутверждённые shared поля.

Связь сохраняется так:

```text
canonical FAILED event
        ↓ failure_id
internal FailureRecord
        ↓ evidence_artifact_ids
internal evidence references
```

Contract test подтверждает, что export не изменяет `FailureRecord.evidence_artifact_ids`.

## 7. Contract tests

Добавлен `tests/test_canonical_adapter.py`.

Проверяется:

1. constants adapter-а совпадают с Integrator-owned JSON Schema;
2. `REVISION_CREATED` точно совпадает с canonical golden fixture;
3. directive acceptance flow экспортируется в правильном sequence;
4. `manufacturing_id`, `installation_id`, `failure_id` сохраняют traceability;
5. внутренние failure evidence references не теряются;
6. naive timestamps отклоняются.

Runtime adapter не читает JSON Schema с файловой системы.

Это сознательное решение: production boundary не зависит от layout repository. Schema/fixture используются contract tests как integration guard.

## 8. Verification

Локально выполнен полный текущий набор Chat 5 tests после добавления adapter-а:

```text
PYTHONPATH=src pytest -q
```

Результат:

```text
8 passed
```

## 9. Решение CR-CHAT5-001

`LifecycleEvent / LifecycleState semantics` считается разрешённым директивой Chat 6:

```text
LifecycleEvent v1 = canonical shared outbound contract
LifecycleState = internal derived projection Chat 5
```

Shared contract Chat 5 не изменял.

## 10. Следующий технический шаг

После повторной проверки следующей orchestrator directive:

1. repository abstraction для lifecycle persistence;
2. отделение in-memory Phase-1 store от production repository interface;
3. explicit physical instance / removal / replacement semantics;
4. persistence prototype;
5. API boundary поверх approved canonical contracts.

AI/semantic search по-прежнему не входит в ближайший этап.
