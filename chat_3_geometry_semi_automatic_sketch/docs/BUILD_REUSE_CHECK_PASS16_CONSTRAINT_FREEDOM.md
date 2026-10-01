# BUILD / REUSE CHECK — Pass 16 Constraint Freedom Diagnosis

**Date:** 2026-10-02  
**Slice owner:** Chat 3 — Geometry & Semi-Automatic Sketch

## Проблема

После Pass 15 система умеет диагностировать глобальные structural conflicts/redundancy, но `CONSISTENT` намеренно не означает `fully constrained`. Нужен read-only способ определить локальное число степеней свободы поддерживаемого sketch, отдельно показать rigid-frame freedom и внутреннюю shape freedom и при этом не превращать диагностику в solver, который двигает геометрию.

## Есть ли готовое open-source решение

Да, существуют полноценные geometric constraint solvers и generic numerical linear-algebra libraries. Они решают более широкую задачу: nonlinear solving, entity movement, large sparse systems и CAD-specific semantics.

## Можно ли использовать

`PARTIAL`.

Повторно используем уже существующие MREA primitives, `ConstraintResolution`, `ConstraintSystemAnalyzer`, verified `DimensionBinding` и общую математическую идею Jacobian rank/nullity. Внешний solver для этого pass не подключается, потому что Pass 16 должен быть только диагностическим и не должен менять geometry state.

## Что используем

- существующий Chat-3 geometry domain;
- существующий `ConstraintSystemAnalyzer` как conflict gate;
- published `ResolvedConstraint` semantics;
- verified measurement bindings;
- Python standard library для finite differences и deterministic rank elimination.

## Что пишем сами

- узкую parameter layout для `POINT` / `LINE` / `CIRCLE` / `ARC`;
- mapping уже поддерживаемых constraints/dimensions в локальные scalar equations;
- finite-difference Jacobian;
- deterministic matrix-rank calculation;
- rigid-body null-mode classification;
- fail-closed topology witness policy для `COINCIDENT`;
- deterministic `ConstraintFreedomDiagnosis`.

## Почему

Это сохраняет separation of concerns: Pass 16 отвечает только на вопрос «сколько локальных степеней свободы ещё остаётся при известных ограничениях», не вводя solver, mutation, новый CAD kernel или новую shared contract semantics.

## Lock-in risk

Средний: equation mapping является Chat-3 internal implementation и привязан к текущему v1 primitive/constraint vocabulary.

Снижение риска:

- public surface ограничен read-only diagnosis;
- unsupported semantics дают `INDETERMINATE`, а не guessed DOF;
- никакие shared contracts не меняются;
- numerical solver позже может заменить internal rank engine без изменения measured-truth policy.

## Fallback

Когда roadmap явно перейдёт к numerical constraint solving/entity movement, локальный diagnostic engine можно заменить или дополнить специализированным solver adapter, сохранив fail-closed truth gates и regression fixtures Pass 16.
