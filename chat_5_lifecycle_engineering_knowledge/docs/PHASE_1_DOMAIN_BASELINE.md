# Chat 5 — Phase 1 Domain Baseline

## Статус

Дата: 2026-09-29  
Slice: Lifecycle & Engineering Knowledge  
Статус: implemented baseline / local verification passed

Этот документ описывает только внутренний baseline Chat 5. Он не определяет shared contracts проекта и не заменяет Integrator-owned schemas.

---

## 1. Цель итерации

Реализовать первый детерминированный lifecycle flow без AI, persistence и внешнего API:

```text
REV01
→ MANUFACTURED
→ INSTALLED
→ FAILED
→ failure evidence retained
→ REV02
→ MANUFACTURED
→ INSTALLED
→ ACTIVE
```

---

## 2. Реализованные компоненты

### Domain models

- `Revision`
- `ManufacturingRecord`
- `Installation`
- `TestRecord`
- `FailureRecord`
- internal `LifecycleEvent`
- internal `LifecycleEventType`
- internal `LifecycleState`

### Application services

- `RevisionService`
- `ManufacturingService`
- `InstallationService`
- `TestService`
- `FailureService`

### Projections / queries

- `LifecycleTimeline`
- `EquipmentPartRegistry`
- `LifecycleStateProjection`
- `RevisionComparison`
- `KnowledgeQueryService`

### Storage baseline

- `InMemoryLifecycleStore`

`InMemoryLifecycleStore` нужен только для проверки domain semantics и invariants до появления утверждённой persistence-схемы.

---

## 3. Основные invariants

Реализовано:

- `revision_id` не может дублироваться;
- `revision_code` не переиспользуется для другой revision того же part;
- parent revision должна существовать и принадлежать тому же part;
- manufacturing record обязан ссылаться на существующую revision;
- installation обязана ссылаться на существующий manufacturing record той же revision;
- test не может быть привязан к manufacturing/installation другой revision;
- failure не может быть привязан к manufacturing/installation другой revision;
- failure требует хотя бы один evidence artifact;
- `estimated_cause` и `confirmed_cause` остаются раздельными полями;
- новая revision не удаляет историю предыдущей;
- current equipment mapping вычисляется из installation history;
- timeline сортируется детерминированно по `occurred_at`, затем по внутреннему sequence.

---

## 4. LifecycleEvent / LifecycleState

В коде они являются **внутренними типами Chat 5**.

Они не считаются реализацией shared contracts.

Текущая локальная гипотеза остаётся:

```text
LifecycleEvent = historical fact
LifecycleState = derived projection
```

До решения Integrator нельзя использовать текущие enum как repository-wide contract.

---

## 5. Equipment mapping

`EquipmentPartRegistry.current_installation()` выбирает последнее событие `INSTALLED` для пары:

```text
equipment_id + position
```

История старых installation records не удаляется.

На этом baseline ещё нет отдельного `REMOVED` event и формальной модели physical part instance. Поэтому registry является MVP projection, а не финальной моделью эксплуатации.

---

## 6. Revision comparison

`RevisionComparison` сейчас сравнивает только данные, которыми владеет Chat 5:

- используемые materials;
- количество failures;
- количество tests;
- derived lifecycle state.

Geometry diff не реализован, потому что geometry принадлежит upstream slice и должен поступать только через утверждённый contract.

---

## 7. Knowledge queries

`KnowledgeQueryService` реализует только детерминированные структурированные запросы:

- какие revision имеют зарегистрированные failures;
- какая revision сейчас является текущей для `equipment_id + position`.

AI, semantic search и автоматические causal conclusions отсутствуют намеренно.

---

## 8. Build / Reuse Check

Проблема: lifecycle domain semantics, historical records, projections и engineering queries.

Есть ли готовое open-source решение: PARTIAL.

Используем позже:

- SQLAlchemy для persistence mapping;
- PostgreSQL как production database baseline;
- pytest для tests;
- FastAPI/Pydantic после появления API/shared contracts.

Пишем сами:

- lifecycle invariants;
- revision history semantics;
- equipment mapping semantics;
- lifecycle projections;
- revision comparison logic;
- engineering knowledge query rules.

Почему: это продуктовая domain logic MREA и она определяется SSOT, а не generic library.

Lock-in risk: низкий на domain layer, если persistence остаётся adapter boundary.

Fallback: текущий in-memory store позволяет тестировать domain logic независимо от ORM/database.

---

## 9. Verification

Локально был выполнен:

```text
PYTHONPATH=src pytest -q
```

Результат:

```text
4 passed
```

Покрыто:

- полный acceptance flow REV01 → failure → REV02 → active;
- сохранение failure evidence;
- current equipment mapping;
- deterministic timeline order;
- revision comparison;
- duplicate revision code rejection;
- cross-revision manufacturing/install mismatch rejection;
- failure evidence invariant;
- разделение estimated и confirmed cause.

---

## 10. Не реализовано

- SQL/PostgreSQL persistence;
- Pydantic/shared contract adapters;
- REST/API endpoints;
- `ArtifactReference` validation against Integrator schema;
- shared `LifecycleEvent` serialization;
- removal/reinstall/decommission flow;
- отдельная physical instance model;
- concurrency/versioning;
- migrations;
- global contract tests;
- CI execution;
- AI/semantic search.

---

## 11. Следующий технический шаг

Следующая итерация Chat 5 должна сначала перечитать актуальный repository state и проверить, появились ли Integrator-owned contracts/fixtures.

Если shared contracts всё ещё отсутствуют, безопасный следующий внутренний шаг:

1. repository abstraction вместо прямой зависимости services от in-memory store;
2. persistence adapter prototype внутри ownership Chat 5;
3. removal/replacement semantics;
4. расширенные timeline/state tests;
5. только после утверждения contracts — Pydantic/API integration.
