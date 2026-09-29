# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Phase 1 domain/runtime baseline implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 от 2026-09-29**

## Назначение области

Эта директория принадлежит Chat 5 и содержит реализацию вертикального слайса **Lifecycle & Engineering Knowledge**.

Слайс отвечает за физическую жизнь детали после этапа CAD:

```text
Revision
→ Manufacturing
→ Installation
→ Test
→ Failure / Success
→ Next Revision
→ Engineering Knowledge
```

## Ownership

Chat 5 отвечает за:

- revisions;
- manufacturing records;
- installation;
- tests;
- failures;
- revision comparison;
- field status;
- equipment mapping;
- lifecycle timeline;
- engineering knowledge queries.

Реализованный Phase 1 содержит:

- `RevisionService`
- `ManufacturingService`
- `InstallationService`
- `TestService`
- `FailureService`
- `RevisionComparison`
- `EquipmentPartRegistry`
- `LifecycleTimeline`
- `LifecycleStateProjection`
- `KnowledgeQueryService`
- `InMemoryLifecycleStore`

## Не входит в ownership

Chat 5 самостоятельно не изменяет:

- camera / Guided Capture;
- Physical Measurement;
- Geometry / Sketch;
- SolidWorks API / CAD adapter;
- shared contracts;
- global architecture;
- contract fixtures Integrator-а.

Cross-slice изменения оформляются через `CHANGE_REQUEST` для Integrator.

## Структура

```text
chat_5_lifecycle_engineering_knowledge/
├── README.md
├── docs/
│   ├── CHAT_5_ROLE.md
│   ├── IMPLEMENTATION_STATE.md
│   └── PHASE_1_DOMAIN_BASELINE.md
├── src/
│   └── mrea_lifecycle/
│       ├── __init__.py
│       ├── models.py
│       ├── projections.py
│       ├── services.py
│       └── store.py
└── tests/
    ├── test_acceptance_flow.py
    └── test_invariants.py
```

## Первый acceptance-flow

```text
REV01
→ manufactured
→ installed
→ failed
→ failure evidence retained
→ REV02
→ manufactured
→ installed
→ active
```

Этот flow реализован и локально проверен.

## Verification

```text
PYTHONPATH=src pytest -q
```

Результат Phase 1:

```text
4 passed
```

## Важное ограничение

`LifecycleEvent`, `LifecycleEventType` и `LifecycleState` в текущем коде являются **внутренними типами Chat 5**, а не shared contracts проекта.

Integrator-owned schemas/fixtures на момент Phase 1 в проверенной структуре repository отсутствовали. Shared contracts не изменялись.

## Документация

- [`docs/CHAT_5_ROLE.md`](docs/CHAT_5_ROLE.md) — роль, ownership, границы и архитектурная модель.
- [`docs/PHASE_1_DOMAIN_BASELINE.md`](docs/PHASE_1_DOMAIN_BASELINE.md) — реализованный Phase 1, invariants, verification и ограничения.
- [`docs/IMPLEMENTATION_STATE.md`](docs/IMPLEMENTATION_STATE.md) — актуальное фактическое состояние и следующий шаг.
