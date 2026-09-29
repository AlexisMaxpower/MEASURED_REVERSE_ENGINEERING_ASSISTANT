# Chat 3 — Build / Reuse Check — Phase 1 Geometry Core

**Дата:** 2026-09-29  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch

## Проблема

Нужен deterministic geometry core, который принимает уже нормализованные примитивы и подтверждённые measurement-данные, строит topology/constraints, связывает measurement anchors с geometry entities и явно фиксирует unresolved/conflict состояния.

## Есть ли готовое open-source решение

PARTIAL.

Готовые библиотеки существуют для CV, computational geometry и constraint solving, но текущая задача включает MREA-specific правила provenance, measurement priority, traceability и deterministic package preparation.

## Можно ли использовать

PARTIAL.

На Phase 1 внешняя runtime dependency не требуется. Базовые операции расстояния, topology и deterministic ordering достаточно малы и прозрачны для реализации на Python standard library.

Позже должны отдельно оцениваться:

- OpenCV для contour/line/circle/arc candidate extraction;
- существующая geometry library для более сложных spatial operations;
- существующий geometry/constraint solver, если локальный минимальный resolver перестанет покрывать требования.

## Что используем сейчас

- Python >= 3.11;
- standard library (`dataclasses`, `math`, `itertools`);
- pytest только как test dependency.

## Что пишем сами

- MREA internal geometry models;
- GeometryGraph;
- deterministic ordering;
- anchor-to-entity association policy;
- measurement binding;
- derived geometry estimate for supported measurement types;
- conflict visibility policy;
- unresolved binding representation;
- constraint candidate generation.

## Почему

Эти части содержат продуктовую семантику MREA и напрямую реализуют инвариант:

```text
verified physical measurement > image-derived geometry
```

Готовая generic geometry library не решает provenance/measurement ownership и не должна самостоятельно определять такую политику.

## Lock-in risk

LOW для Phase 1: runtime external dependencies отсутствуют.

## Fallback

Если будущие geometry/CV задачи потребуют сторонней библиотеки, внутренние модели и pipeline остаются boundary layer. Provider/adapter можно заменить без изменения shared contract при условии сохранения deterministic internal semantics.

## Что намеренно не реализовано сейчас

- image contour extraction;
- OpenCV primitive detection;
- general constraint solver;
- canonical `MeasurementPackage` adapter;
- canonical `SketchPackage` serializer;
- pixel→MAT_XY_MM calibration transform.

Последние три пункта зависят от Integrator contracts/fixtures и не должны быть выдуманы Chat 3.
