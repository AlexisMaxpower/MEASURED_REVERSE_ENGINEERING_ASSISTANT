# Chat 5 — Lifecycle & Engineering Knowledge

Статус: **initialized / documentation baseline**  
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

Планируемые компоненты:

- `RevisionService`
- `ManufacturingService`
- `InstallationService`
- `TestService`
- `FailureService`
- `RevisionComparison`
- `EquipmentPartRegistry`
- `LifecycleTimeline`
- `KnowledgeQueryService`

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

## Документация

- [`docs/CHAT_5_ROLE.md`](docs/CHAT_5_ROLE.md) — роль, границы, модель, контракты, правила и план реализации.
- [`docs/IMPLEMENTATION_STATE.md`](docs/IMPLEMENTATION_STATE.md) — текущее фактическое состояние области, проверки, ограничения и следующий шаг.

## Первый acceptance-flow

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

Первый кодовый этап должен реализовать этот сценарий детерминированно через fixtures, без AI.

## Текущее состояние

На момент инициализации области создана только документационная база Chat 5. Runtime/domain/persistence/API код ещё не реализован и не должен считаться существующим до отдельной зафиксированной итерации.