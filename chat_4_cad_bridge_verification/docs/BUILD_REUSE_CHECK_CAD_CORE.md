# Chat 4 — Build / Reuse Check: CAD Core Baseline

**Дата:** 2026-09-29  
**Scope:** canonical boundary, internal CAD model, SVG/DXF export, verification

## Internal CAD model

**Проблема:** vendor-neutral representation между canonical SketchPackage и CAD adapters.  
**Reuse:** PARTIAL.  
**Решение:** минимальные immutable Python dataclasses только для supported 2D baseline.  
**Почему:** полноценный CAD kernel не нужен для transport/export boundary.  
**Lock-in:** LOW.

## Canonical contracts

**Проблема:** cross-slice DTO и policies.  
**Reuse:** YES — только Integrator-owned contracts.  
**Используем:**

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `tests/fixtures/contracts/`.

Chat 4 не создаёт параллельные shared DTO.

## SVG

**Проблема:** простой deterministic 2D interchange/preview.  
**Reuse:** стандартная XML/string generation достаточна для текущего subset.  
**Fallback:** XML/SVG library при усложнении metadata/styles/transforms.  
**Lock-in:** LOW.

## DXF

**Проблема:** корректный CAD interchange без собственной реализации DXF serialization.  
**Reuse:** YES.  
**Используем:** `ezdxf==1.4.4`, R12 writer.  
**Пишем сами:** только mapping internal entities → public `ezdxf` API.  
**Validation:** generated DXF parse-back через `ezdxf.read()`.  
**Lock-in:** LOW/MEDIUM; exporter скрыт за `CadExporter`.

## Verification

**Проблема:** MREA-specific no-silent-correction numerical CAD transfer verification.  
**Reuse:** canonical policy + standard arithmetic.  
**Пишем сами:** domain state transitions и report mapping.  
**Canonical tolerance:** `1e-6 mm`, `1e-6 deg`.  
**Lock-in:** LOW.

## JSON Schema contract tests

**Проблема:** гарантировать совместимость local mapper с Integrator-owned schemas.  
**Reuse:** YES.  
**Используем:** `jsonschema==4.26.0` только как development/test dependency.  
**Пишем сами:** golden mapping assertions и exact fixture comparison.  
**Почему:** дублировать JSON Schema validator не имеет смысла.  
**Lock-in:** LOW.

## Dependencies

Runtime:

```text
ezdxf==1.4.4
```

Development/tests:

```text
jsonschema==4.26.0
```
