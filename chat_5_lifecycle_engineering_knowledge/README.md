# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **Phase 2 canonical LifecycleEvent adapter implemented**  
Проект: **MREA — Measured Reverse Engineering Assistant**  
Источник истины: **MREA SSOT v0.1 от 2026-09-29**  
Текущая директива: **OD-2026-09-29-001**

## Назначение области

Эта директория принадлежит Chat 5 и содержит vertical slice **Lifecycle & Engineering Knowledge**:

```text
Revision
→ Manufacturing
→ Installation
→ Test
→ Failure / Success
→ Next Revision
→ Engineering Knowledge
```

## Реализовано

Phase 1:

- lifecycle domain models;
- `RevisionService`;
- `ManufacturingService`;
- `InstallationService`;
- `TestService`;
- `FailureService`;
- `LifecycleTimeline`;
- `EquipmentPartRegistry`;
- `LifecycleStateProjection`;
- `RevisionComparison`;
- `KnowledgeQueryService`;
- `InMemoryLifecycleStore`.

Phase 2:

- `CanonicalLifecycleEventAdapter`;
- canonical `mrea.lifecycle-event.v1` serialization;
- deterministic ordered export;
- canonical contract/golden tests;
- evidence-preserving outbound boundary.

## Contract boundary

Chat 5 не изменяет shared contracts.

Canonical inputs принадлежат Integrator / Chat 6:

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/lifecycle_event_v1.json`.

Текущая семантика:

```text
LifecycleEvent v1 = canonical shared outbound contract
LifecycleState = internal derived projection
```

Rich Revision/Manufacturing/Installation/Test/Failure models остаются внутренними Chat 5.

## Структура

```text
chat_5_lifecycle_engineering_knowledge/
├── ORCHESTRATOR_DIRECTIVE.md
├── README.md
├── docs/
│   ├── CHAT_5_ROLE.md
│   ├── IMPLEMENTATION_STATE.md
│   ├── PHASE_1_DOMAIN_BASELINE.md
│   └── PHASE_2_CANONICAL_LIFECYCLE_ADAPTER.md
├── src/
│   └── mrea_lifecycle/
│       ├── __init__.py
│       ├── adapters.py
│       ├── models.py
│       ├── projections.py
│       ├── services.py
│       └── store.py
└── tests/
    ├── test_acceptance_flow.py
    ├── test_canonical_adapter.py
    └── test_invariants.py
```

## Verification

Локально:

```text
PYTHONPATH=src pytest -q
8 passed
```

Repository-wide CI в этой итерации не запускался.

## Документация

- `docs/CHAT_5_ROLE.md` — role baseline.
- `docs/PHASE_1_DOMAIN_BASELINE.md` — internal lifecycle baseline.
- `docs/PHASE_2_CANONICAL_LIFECYCLE_ADAPTER.md` — canonical boundary и contract tests.
- `docs/IMPLEMENTATION_STATE.md` — актуальный implementation state и следующий шаг.

## Следующий шаг

Перед каждой итерацией сначала читать `ORCHESTRATOR_DIRECTIVE.md` и canonical inputs.

Если Chat 6 не изменит приоритет: repository abstraction → physical instance/removal/replacement semantics → persistence prototype → API boundary.
