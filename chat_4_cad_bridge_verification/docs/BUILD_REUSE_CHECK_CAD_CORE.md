# Chat 4 — Build / Reuse Check: CAD Core Baseline

**Дата:** 2026-09-29  
**Scope:** internal CAD model, SVG/DXF export, pure verification core

## 1. Generic CAD model

**Проблема:** нужен vendor-neutral внутренний слой между будущим `SketchPackage` mapper и конкретными exporters/adapters.  
**Есть ли готовое open-source решение:** YES.  
**Можно ли использовать:** PARTIAL.  
**Что используем:** стандартные immutable Python structures для небольшого internal boundary.  
**Что пишем сами:** минимальный internal model для Point/Line/Circle/Arc/Polyline и deterministic ordering.  
**Почему:** shared `SketchPackage` contract ещё не опубликован; тяжёлый CAD kernel здесь не нужен и создал бы лишний lock-in.  
**Lock-in risk:** LOW.  
**Fallback:** заменить internal mapping/adapters после утверждения repository architecture без изменения shared contracts.

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

**Проблема:** корректный перенос простых 2D entities в CAD interchange format без собственной реализации DXF serialization rules.  
**Есть ли готовое open-source решение:** YES — `ezdxf`.  
**Можно ли использовать:** YES.  
**Что используем:** `ezdxf==1.4.4`, `ezdxf.addons.r12writer.r12writer`, ASCII DXF R12, `fixed_tables=True`.  
**Что пишем сами:** только mapping `CadSketch` entities → публичные операции `r12writer` (`add_point`, `add_line`, `add_circle`, `add_arc`, `add_polyline_2d`).  
**Почему:** SSOT прямо запрещает без причины переписывать стабильный DXF tooling. `ezdxf` предоставляет готовый R12 writer, поэтому low-level group-code serialization удалена из ownership Chat 4.  
**Construction geometry:** остаётся на layer `0`, но получает стандартный `DASHED` linetype из fixed R12 tables.  
**Validation:** generated DXF повторно читается через `ezdxf.read()` в unit test; проверяются entity types и construction linetype.  
**Lock-in risk:** LOW/MEDIUM — exporter зависит от публичного API `r12writer`, но boundary остаётся `CadExporter`, поэтому implementation можно заменить.  
**Fallback:** перейти на основной `ezdxf` document API или другой зрелый DXF writer без изменения internal CAD model/shared contracts.

## 4. Verification core

**Проблема:** сравнить verified physical dimensions с CAD read-back без silent correction.  
**Есть ли готовое open-source решение:** общие numeric/testing libraries существуют, но доменная policy специфична MREA.  
**Можно ли использовать:** PARTIAL.  
**Что используем:** стандартная арифметика Python.  
**Что пишем сами:** status mapping `VERIFIED/MISMATCH/MISSING/CONSTRAINT_CONFLICT`, explicit tolerance input, deterministic report ordering.  
**Почему:** это уникальная доменная логика MREA; tolerance намеренно не угадывается и обязана приходить от утверждённой policy/contract boundary.  
**Lock-in risk:** LOW.  
**Fallback:** заменить numeric representation после Integrator ADR, сохранив no-silent-correction invariant.

## Dependencies

Runtime dependency Chat 4 baseline:

```text
ezdxf==1.4.4
```

Тесты остаются на standard-library `unittest`; отдельная test framework dependency не требуется.

## Ограничение baseline

Этот код **не определяет** `SketchPackage`, `CADPackage` или `CADVerificationReport` как shared contracts. Он является внутренним Chat 4 core. Contract mappers появятся только после публикации Integrator-owned schemas/fixtures.
