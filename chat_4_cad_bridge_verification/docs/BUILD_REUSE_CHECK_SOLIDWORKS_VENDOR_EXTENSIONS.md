# BUILD / REUSE CHECK — SOLIDWORKS vendor extensions

**Project:** MREA  
**Slice:** Chat 4B — SOLIDWORKS 2026 CAD Agent & Real-Host Integration  
**Pass:** 2  
**Date:** 2026-09-29

## Проблема

Расширить уже существующий SOLIDWORKS 2026 CAD Agent без изменения canonical contracts:

- native `POINT`;
- native `ARC`;
- canonical sketch relations/constraints, когда их семантика однозначна;
- solver-status safety signal;
- отдельный real-host smoke test для vendor-specific возможностей.

`ANGLE` рассматривается отдельно, потому что `SketchPackage v1` содержит только `entity_ids` + numeric angle и не задаёт ветвь/квадрант angular dimension.

## Есть ли готовое open-source решение

Для низкоуровневой работы с SOLIDWORKS повторная реализация не нужна: используется официальный SOLIDWORKS API/COM.

## Можно ли использовать

**YES / PARTIAL**

Используем официальный API для:

- `ISketchManager.CreatePoint`;
- `ISketchManager.CreateArc`;
- `ISketch.RelationManager`;
- `ISketchRelationManager.AddRelation`;
- `ISketch.GetConstrainedStatus`;
- `IModelDoc2.AddDimension2`;
- существующие `SetSystemValue3` / `GetSystemValue3`;
- существующий `SaveAs`.

## Что пишем сами

- deterministic mapping MREA vendor protocol → SOLIDWORKS API;
- validation of supported entity/constraint combinations;
- explicit rejection of ambiguous canonical semantics;
- constraint-conflict propagation;
- direct vendor smoke runner;
- handoff to Primary Chat 4.

## Почему

Уникальная часть MREA — traceability, no-silent-approximation policy и vendor boundary. Геометрические примитивы, relations и solver предоставляет SOLIDWORKS.

## Lock-in risk

Средний внутри vendor adapter, низкий для canonical/domain слоя.

SOLIDWORKS types остаются только внутри:

```text
chat_4_cad_bridge_verification/solidworks_agent/
```

Process protocol остаётся JSON и не переносит COM objects наружу.

## Fallback

Если конкретная canonical relation не может быть однозначно выражена в SOLIDWORKS без дополнительных данных:

1. не угадывать;
2. вернуть explicit vendor failure;
3. зафиксировать integration question для Primary Chat 4 / Chat 6;
4. не менять shared contract в Side Chat 4B.
