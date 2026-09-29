# Chat 5 — Lifecycle & Engineering Knowledge

## 1. Статус документа

- Проект: **MREA — Measured Reverse Engineering Assistant**
- Роль: **Chat 5**
- Vertical slice: **Lifecycle & Engineering Knowledge**
- SSOT baseline: **v0.1, 2026-09-29**
- Статус: **role baseline / pre-implementation**
- Язык документации: русский
- Язык идентификаторов кода: английский

Этот документ уточняет работу Chat 5 в рамках SSOT и не заменяет shared contracts Integrator-а.

---

## 2. Цель слайса

Chat 5 превращает изготовленную CAD-ревизию из статического артефакта в трассируемую инженерную сущность с физической историей.

Целевая цепочка:

```text
CAD / Revision
↓
Manufacturing
↓
Installation
↓
Test
↓
Failure / Success
↓
Revision change
↓
Accumulated engineering knowledge
```

Система должна позволять восстановить:

- какая ревизия была изготовлена;
- из какого материала и каким способом;
- где она установлена;
- какие испытания прошла;
- находится ли она в эксплуатации;
- когда и как произошёл отказ;
- какое место/feature связано с отказом;
- какая следующая ревизия была создана;
- что изменилось между ревизиями;
- какие решения исторически работали или не работали.

---

## 3. Ownership

Chat 5 владеет следующей функциональностью:

1. `Revision`
2. `ManufacturingRecord`
3. `Installation`
4. `TestRecord`
5. `FailureRecord`
6. revision comparison
7. field status
8. equipment mapping
9. lifecycle timeline
10. engineering knowledge queries

Базовые компоненты из SSOT:

```text
RevisionService
ManufacturingService
InstallationService
TestService
FailureService
RevisionComparison
EquipmentPartRegistry
LifecycleTimeline
KnowledgeQueryService
```

---

## 4. Что Chat 5 не делает

Chat 5 не владеет и самостоятельно не изменяет:

- camera core;
- Guided Capture;
- Physical Measurement;
- OCR semantics;
- GeometryGraph;
- SketchPackage generation;
- CAD-native API;
- SolidWorks adapter;
- shared contracts;
- shared domain;
- global fixtures;
- global architecture;
- release gates.

Если входного shared contract недостаточно, создаётся `CHANGE_REQUEST` для Integrator.

---

## 5. Shared contracts, на которые опирается слайс

Согласно SSOT, shared contracts принадлежат Integrator. Для Chat 5 потенциально значимы:

- `ProjectContract`
- `CADPackage`
- `CADVerificationReport`
- `LifecycleEvent`
- `ArtifactReference`

Chat 5 не меняет их схемы самостоятельно.

### 5.1. Контрактная неоднозначность

В Product Matrix downstream output Chat 5 указан как `LifecycleState`, но в перечне shared contracts определён `LifecycleEvent`, а `LifecycleState` отсутствует как отдельный shared contract.

До решения Integrator Chat 5 использует следующую внутреннюю архитектурную гипотезу:

```text
LifecycleEvent = persisted historical fact
LifecycleState = derived read model / projection
```

Это **не изменение SSOT**, а локальная модель-кандидат.

### 5.2. Change Request для Integrator

```text
CHANGE_REQUEST

Requester: Chat 5
Contract: LifecycleEvent / LifecycleState
Problem:
Product Matrix определяет output Chat 5 как LifecycleState, но Shared Contracts и fixtures определяют LifecycleEvent.

Current behavior:
LifecycleEvent существует как shared contract.
LifecycleState формально не определён.

Requested change:
Уточнить один из вариантов:
A) LifecycleEvent — persisted event, LifecycleState — derived/read model;
B) LifecycleState не является shared contract и остаётся внутренней projection Chat 5.

Reason:
Нужно зафиксировать публичный API и contract tests до кодовой интеграции.

Affected chats:
Chat 5, Integrator, будущие consumers lifecycle data.

Backward compatible:
YES, если LifecycleState остаётся projection.

Migration:
Не требуется до фиксации contracts v1.
```

---

## 6. Базовая domain model

Минимальная модель должна выражать следующие связи:

```text
Project
└── Part
    ├── Revision REV01
    │   ├── ManufacturingRecord*
    │   ├── Installation*
    │   ├── TestRecord*
    │   └── FailureRecord*
    │
    ├── Revision REV02
    │   ├── ManufacturingRecord*
    │   ├── Installation*
    │   ├── TestRecord*
    │   └── FailureRecord*
    │
    └── Revision REVNN

Equipment
└── installed Part Revision
```

`*` означает 0..N записей, если Integrator/shared contract не установит более жёсткое ограничение.

---

## 7. Revision

`Revision` представляет конкретную инженерную версию детали.

Минимальные ожидаемые свойства внутренней модели:

```text
revision_id
part_id
revision_code
parent_revision_id?
created_at
status
notes?
source_cad_artifact?
```

### Инварианты

- revision code не должен молча переиспользоваться для другой геометрии;
- новая ревизия не должна уничтожать историю предыдущей;
- связь parent → child должна быть трассируемой;
- изменение ревизии должно быть объяснимо через diff и/или explicit notes;
- physical records всегда относятся к конкретной revision.

---

## 8. ManufacturingRecord

SSOT определяет минимум:

- material;
- batch;
- method;
- printer/machine;
- print profile;
- contractor;
- date;
- cost;
- post-processing.

Ожидаемая связь:

```text
Revision 1 ── N ManufacturingRecord
```

Одна revision может быть изготовлена несколько раз разными партиями и настройками.

### Инварианты

- manufacturing record не должен переписывать revision;
- параметры изготовления сохраняются как исторический факт;
- повторное изготовление создаёт новую запись;
- стоимость и производственные параметры не должны теряться при следующей ревизии.

---

## 9. Installation

SSOT определяет минимум:

- date;
- equipment;
- position;
- technician;
- notes.

Installation связывает конкретный физический экземпляр/revision с конкретным оборудованием и позицией.

Ключевая задача `EquipmentPartRegistry`:

```text
Equipment + position
→ какая revision/instance установлена сейчас
→ когда установлена
→ предыдущие установки
→ текущий field status
```

### Инварианты

- нельзя терять старую installation history;
- замена детали не переписывает старую установку;
- current mapping должен быть производным от истории или явно управляемым консистентным состоянием;
- оборудование и позиция должны позволять отличать несколько одинаковых деталей.

---

## 10. TestRecord

SSOT определяет минимум:

- test type;
- conditions;
- result;
- photo;
- conclusion.

Tests могут выполняться:

- после manufacturing;
- до installation;
- после installation;
- после ремонта/изменений;
- при диагностике failure.

### Инварианты

- test result относится к конкретной revision/physical context;
- evidence/artifact не удаляется при изменении conclusion;
- повторный test создаёт новую запись;
- положительный test не означает автоматически, что revision никогда не откажет.

---

## 11. FailureRecord

SSOT определяет минимум:

- date;
- failure type;
- damage location;
- photos;
- circumstances;
- estimated cause;
- confirmed cause;
- related feature.

### Разделение факта и гипотезы

Failure model должна явно разделять:

```text
Observed fact
Estimated cause
Confirmed cause
```

`estimated cause` не должна автоматически становиться `confirmed cause`.

### Инварианты

- failure относится к конкретной revision и, где возможно, installation/physical instance;
- evidence сохраняется;
- related feature может быть неизвестен;
- отсутствие подтверждённой причины не блокирует регистрацию failure;
- изменение гипотезы причины не удаляет исходные наблюдения.

---

## 12. Lifecycle events и timeline

Внутренний event-oriented baseline:

```text
REVISION_CREATED
MANUFACTURED
INSTALLED
TESTED
FAILED
REMOVED
REINSTALLED
DECOMMISSIONED
```

Этот список пока не является shared enum и может быть изменён только после проверки существующего `LifecycleEvent` contract.

`LifecycleTimeline` должен:

1. принимать исторические записи;
2. сортировать их детерминированно;
3. связывать события с revision/instance/equipment;
4. не скрывать конфликтующие факты;
5. строить читаемую временную шкалу;
6. позволять вывести current field state без потери истории.

---

## 13. LifecycleState как projection

Предпочтительный внутренний подход до решения Integrator:

```text
append historical records/events
↓
LifecycleTimeline
↓
LifecycleState projection
```

Примеры возможного текущего состояния:

```text
DRAFT
MANUFACTURED
INSTALLED
ACTIVE
FAILED
REMOVED
DECOMMISSIONED
```

Это не утверждённый shared enum.

Главное правило: current state не должен заменять timeline.

---

## 14. RevisionComparison

`RevisionComparison` должен отвечать не только "REV02 новее REV01", но и структурированно показывать изменения.

Минимальные категории сравнения:

- metadata;
- manufacturing target;
- material;
- known geometry parameters, если доступны через approved upstream contract;
- lifecycle outcomes;
- failures;
- tests;
- notes/reasons for revision.

Пример инженерно полезного результата:

```text
REV01
material = PETG
wall = 2.0 mm
fillet = 0.5 mm
failure = crack near H2 after 18 days

REV02
material = PETG
wall = 3.2 mm
fillet = 2.0 mm
status = active, no failures recorded
```

Система не должна автоматически объявлять изменение "причиной успеха" без достаточных данных.

---

## 15. Engineering Knowledge

Engineering Knowledge строится поверх структурированной lifecycle history.

Система должна со временем уметь отвечать:

- какие ревизии ломались;
- какие материалы использовались;
- какие материалы показывали лучшие/худшие результаты в конкретных наблюдаемых условиях;
- где происходили failures;
- какие geometry changes сопровождали изменение результата;
- какая revision стоит на конкретном оборудовании;
- какие решения повторяются у похожих деталей;
- какие evidence/artifacts подтверждают вывод.

### Важное ограничение

На первой фазе `KnowledgeQueryService` должен быть детерминированным структурированным query layer.

AI/LLM не внедряется раньше накопления структурированных lifecycle records.

---

## 16. AI policy для Chat 5

Допустимо позже:

- semantic search;
- summarization;
- поиск похожих lifecycle cases;
- анализ failure history;
- candidate explanations;
- recommendation candidates.

Недопустимо:

- выдумывать failure;
- менять confirmed records;
- превращать estimated cause в confirmed cause без подтверждения;
- удалять evidence;
- выдавать корреляцию между revision change и успехом как доказанную причинность;
- скрывать неопределённость.

---

## 17. Первый acceptance-flow

Обязательный baseline:

```text
REV01
→ manufactured
→ installed
→ failed
→ failure evidence
→ REV02
→ manufactured
→ installed
→ active
```

Проверяется, что:

- обе revisions существуют независимо;
- manufacturing history сохранена;
- installation history сохранена;
- failure связан именно с REV01;
- evidence доступен;
- REV02 не переписывает REV01;
- equipment registry показывает актуальную revision;
- timeline содержит всю цепочку;
- current state соответствует последнему непротиворечивому состоянию.

---

## 18. Build / Reuse Check

### Проблема

Нужно хранить lifecycle history, строить текущие projections, сравнивать revisions и выполнять инженерные запросы.

### Есть ли готовое open-source решение

Да, частично: ORM, SQL database, query layer, migration tools, generic event patterns.

### Можно ли использовать

`PARTIAL`

### Что используем

- PostgreSQL — persistence baseline проекта;
- SQLAlchemy — ORM/persistence abstraction;
- Pydantic — validation DTO/domain boundary;
- FastAPI — API baseline;
- pytest — tests.

### Что пишем сами

- MREA lifecycle domain rules;
- revision semantics;
- manufacturing/install/test/failure workflow;
- EquipmentPartRegistry;
- lifecycle projection;
- revision comparison;
- engineering knowledge semantics;
- traceability between physical outcome and revision.

### Почему

Уникальность находится в инженерном workflow и provenance/history, а не в реализации СУБД или generic event framework.

### Lock-in risk

Низкий при сохранении domain layer независимым от конкретной БД/API.

### Fallback

Обычная relational persistence без event-sourcing framework. Не внедрять сложную инфраструктуру до появления подтверждённой необходимости.

---

## 19. Предпочтительная реализация по этапам

### Phase L0 — Contract alignment

- проверить актуальные shared contracts/fixtures;
- разрешить `LifecycleEvent` vs `LifecycleState`;
- зафиксировать входные IDs и ArtifactReference semantics.

### Phase L1 — Domain baseline

- Revision;
- ManufacturingRecord;
- Installation;
- TestRecord;
- FailureRecord;
- invariants;
- deterministic unit tests.

### Phase L2 — Persistence and services

- repositories;
- CRUD только там, где соответствует domain workflow;
- service-level transition validation;
- audit/history preservation.

### Phase L3 — Timeline and field state

- LifecycleTimeline;
- EquipmentPartRegistry;
- current state projection;
- conflict detection.

### Phase L4 — Revision comparison

- parent/child revision relationships;
- structured diff;
- lifecycle outcome comparison.

### Phase L5 — KnowledgeQueryService v1

- deterministic structured queries;
- no LLM dependency.

### Phase L6 — Integration

- consume Integrator fixtures;
- contract tests;
- API integration;
- golden lifecycle fixture.

### Phase L7 — Engineering Knowledge / AI later

После появления достаточных данных:

- semantic search;
- similar parts;
- failure analysis;
- revision explanations;
- recommendation candidates.

---

## 20. Testing strategy

### Unit

Проверяются domain invariants каждого компонента.

### Contract

Проверяется чтение утверждённого `LifecycleEvent` и связанных shared contracts.

### Lifecycle transition tests

Проверяются допустимые и недопустимые переходы.

### History preservation

Проверяется, что новая запись не уничтожает предыдущую.

### Golden lifecycle flow

Input fixture → deterministic timeline/current state.

### Equipment mapping

Проверяется замена REV01 → REV02 на одной позиции с сохранением истории.

### Failure traceability

Failure → revision → installation/equipment → evidence.

### Knowledge query tests

Одинаковые structured records → одинаковый query result.

---

## 21. Definition of Done Chat 5

Слайс не считается завершённым, пока:

- пользовательский lifecycle flow не работает;
- domain model отсутствует хотя бы для одного обязательного lifecycle record;
- persistence/API отсутствуют там, где они нужны;
- upstream shared contract не читается;
- downstream data/projection не создаётся;
- contract tests не проходят;
- fixture невалиден;
- ошибки/конфликты скрываются;
- documentation не обновлена;
- затронуты чужие ownership-модули без решения Integrator;
- присутствуют незадокументированные workaround.

---

## 22. Текущие открытые вопросы

1. Формальная схема `LifecycleEvent` ещё должна быть прочитана из Integrator-owned fixture/contract, когда он появится.
2. Нужно решение Integrator по роли `LifecycleState`.
3. Нужно определить, существует ли отдельная сущность physical instance/serial экземпляра или manufacturing record одновременно играет эту роль.
4. Нужно определить approved способ ссылаться на GeometryFeature из FailureRecord без нарушения ownership Chat 3.
5. Нужно определить semantics удаления/исправления ошибочно введённого lifecycle факта: immutable correction event или versioned record.
6. Нужно определить точный набор lifecycle statuses только после contracts alignment.

Ни один из этих пробелов не должен заполняться скрытыми предположениями в production code.

---

## 23. Первый следующий кодовый шаг

После появления/проверки Integrator contracts:

1. создать внутренние domain entities Chat 5;
2. зафиксировать invariants unit tests;
3. реализовать golden flow `REV01 → failed → REV02 → active` на fixture data;
4. только после этого добавлять persistence/API.

AI не является частью первого кодового шага.