# BUILD / REUSE CHECK — Chat 1 Phase 1

**Дата:** 2026-09-29  
**Scope:** Project domain, CapturePlan, local project persistence.

## Project/domain validation

**Проблема:** нужна строгая валидация внутренних моделей Chat 1 до публикации shared contracts Integrator.

**Есть ли готовое open-source решение:** да — Pydantic v2.

**Можно ли использовать:** YES.

**Что используем:** Pydantic `BaseModel`, enums, validators, JSON serialization.

**Что пишем сами:** MREA-specific domain models and application rules.

**Почему:** generic schema/validation уже решены библиотекой; ценность MREA находится в workflow и инженерных правилах.

**Lock-in risk:** низкий/средний; модели используют API Pydantic v2, но domain semantics не завязаны на FastAPI.

**Fallback:** Python dataclasses + explicit serialization layer, если Pydantic перестанет удовлетворять требованиям.

## Local persistence

**Проблема:** R1 требует создавать и восстанавливать project, а capture workflow обязан работать offline-first.

**Есть ли готовое open-source решение:** существует много БД/ORM, но на этом этапе repository-wide persistence architecture Integrator ещё не утверждена.

**Можно ли использовать:** PARTIAL.

**Что используем:** стандартные `pathlib` + atomic `os.replace` для внутреннего JSON repository.

**Что пишем сами:** тонкий `ProjectRepository` protocol и `JsonProjectRepository`.

**Почему:** это даёт реальное локальное восстановление без навязывания PostgreSQL/SQLAlchemy всему проекту и не создаёт shared contract. Реализация скрыта за repository interface и заменяема.

**Lock-in risk:** низкий.

**Fallback:** SQLite/SQLAlchemy adapter после решения Integrator о persistence architecture.

## CapturePlan

**Проблема:** сформировать детерминированный план съёмки из поддерживаемых SSOT видов.

**Есть ли готовое open-source решение:** нет необходимости; это MREA product logic.

**Можно ли использовать:** NO для готового workflow.

**Что используем:** только стандартные Python collections/enums.

**Что пишем сами:** deterministic ordering, duplicate elimination, required/optional marking.

**Почему:** CapturePlan — часть уникального guided reverse-engineering workflow.

**Lock-in risk:** низкий.

**Fallback:** rule engine later, если recommendation logic существенно усложнится.
