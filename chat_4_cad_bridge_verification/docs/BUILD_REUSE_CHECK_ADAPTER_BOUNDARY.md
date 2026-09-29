# Chat 4 — Build / Reuse Check: CAD Adapter Boundary

**Дата:** 2026-09-29  
**Scope:** vendor-neutral CAD adapter/read-back boundary and deterministic TEST_DOUBLE

## Problem

Нужна тестируемая граница между canonical `SketchPackage` и будущими vendor CAD adapters до появления реального SOLIDWORKS runtime в CI/test environment.

Граница должна:

- сохранять `dimension_id` и nullable `measurement_id`;
- связывать canonical dimension с vendor-specific handle/name;
- нормализовать CAD read-back к `mm` / `deg`;
- передавать constraint conflicts явно;
- позволять полностью прогнать canonical golden flow без установленного SOLIDWORKS;
- не включать vendor policy в verification core.

## Open-source solution

Готовые CAD SDK и mocking frameworks существуют, но они не определяют доменный MREA contract `dimension_id → vendor dimension ref → normalized read-back`.

## Use

**PARTIAL.**

На этом слое не добавляется внешняя runtime dependency. Стандартные Python `Protocol`/`dataclass` используются для границы и test double.

`ezdxf` остаётся отдельной зависимостью generic DXF exporter и не используется как vendor-adapter abstraction.

## What MREA writes

- `CadAdapter` protocol;
- `CadDimensionBinding`;
- `CadReadBackDimension`;
- `CadReadBack`;
- `CadAdapterResult`;
- deterministic `TestDoubleCadAdapter`;
- canonical `execute_cad_transfer_v1` orchestration function.

## Why custom

Это небольшой доменный boundary, специфичный MREA. Он не заменяет CAD kernel или SOLIDWORKS SDK, а изолирует их от shared contracts и pure verification logic.

## Lock-in

**LOW.**

Vendor adapters подключаются за `CadAdapter` boundary. TEST_DOUBLE не используется как production CAD implementation.

## Fallback

Если SOLIDWORKS adapter потребует асинхронную/process-isolated boundary или отдельный Windows service, внешний transport можно заменить, сохранив normalized result semantics:

`dimension_id + measurement_id + vendor_dimension_ref + read-back value/unit + conflicts`.

## Verification rule

Vendor adapter обязан вернуть значения в canonical units (`mm` / `deg`). Unit mismatch отклоняется до numerical comparison и не маскируется как `MISMATCH`.
