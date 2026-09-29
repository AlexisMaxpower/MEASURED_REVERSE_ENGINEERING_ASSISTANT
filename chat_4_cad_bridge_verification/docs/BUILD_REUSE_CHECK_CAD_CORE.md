# Chat 4 — Build / Reuse Check: CAD Core Baseline

**Дата:** 2026-09-29  
**Scope:** internal CAD model, SVG/DXF export, pure verification core

## 1. Generic CAD model

**Проблема:** нужен vendor-neutral внутренний слой между будущим `SketchPackage` mapper и конкретными exporters/adapters.  
**Есть ли готовое open-source решение:** YES.  
**Можно ли использовать:** PARTIAL.  
**Что используем:** только стандартные структуры Python на первом baseline.  
**Что пишем сами:** минимальный immutable internal model для Point/Line/Circle/Arc/Polyline и deterministic ordering.  
**Почему:** shared `SketchPackage` contract ещё не опубликован; подключение тяжёлого CAD kernel сейчас создаст лишний lock-in и не решит отсутствующую contract boundary.  
**Lock-in risk:** LOW.  
**Fallback:** заменить внутренний model mapper/adapters после утверждения repository architecture без изменения shared contracts.

## 2. SVG

**Проблема:** детерминированный перенос простой 2D geometry в человекочитаемый interchange/preview format.  
**Есть ли готовое open-source решение:** YES.  
**Можно ли использовать:** YES, но не требуется для baseline.  
**Что используем:** стандартная строковая XML generation без внешней runtime dependency.  
**Что пишем сами:** mapping internal entities → SVG primitives.  
**Почему:** поддерживаемый subset мал, формат прост, внешняя библиотека пока не даёт достаточной дополнительной ценности.  
**Lock-in risk:** LOW.  
**Fallback:** перейти на XML/SVG library, если появятся сложные styles/metadata/transforms.

## 3. DXF

**Проблема:** перенос простых 2D entities в CAD interchange format.  
**Есть ли готовое open-source решение:** YES (например, специализированные DXF libraries).  
**Можно ли использовать:** PARTIAL.  
**Что используем:** dependency-free ASCII DXF R12 subset для baseline tests.  
**Что пишем сами:** только минимальный exporter Point/Line/Circle/Arc/Polyline.  
**Почему:** текущая задача — проверить architecture и deterministic mapping; canonical `SketchPackage` ещё отсутствует. Полноценный DXF parser/writer самостоятельно не строится.  
**Lock-in risk:** MEDIUM, если baseline exporter начать расширять в полноценную библиотеку.  
**Fallback:** при росте DXF scope заменить exporter на зрелую DXF library за тем же `CadExporter` interface.

## 4. Verification core

**Проблема:** сравнить verified physical dimensions с CAD read-back без silent correction.  
**Есть ли готовое open-source решение:** общие numeric/testing libraries существуют, но доменная policy специфична MREA.  
**Можно ли использовать:** PARTIAL.  
**Что используем:** стандартная арифметика Python.  
**Что пишем сами:** status mapping `VERIFIED/MISMATCH/MISSING/CONSTRAINT_CONFLICT`, explicit tolerance input, deterministic report ordering.  
**Почему:** это уникальная доменная логика MREA; tolerance намеренно не угадывается и обязана приходить от утверждённой policy/contract boundary.  
**Lock-in risk:** LOW.  
**Fallback:** заменить numeric representation после Integrator ADR, сохранив no-silent-correction invariant.

## Ограничение baseline

Этот код **не определяет** `SketchPackage`, `CADPackage` или `CADVerificationReport` как shared contracts. Он является внутренним Chat 4 core. Contract mappers появятся только после публикации Integrator-owned schemas/fixtures.
