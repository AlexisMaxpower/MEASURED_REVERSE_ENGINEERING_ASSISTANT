# IMPLEMENTATION_REPORT — Chat 4 Canonical CAD Boundary

**Дата:** 2026-09-29  
**Slice:** CAD Bridge & Verification  
**Canonical baseline:** `mrea.contracts.v1`

## 1. Что реализовано

- canonical `SketchPackage v1 → MappedSketchPackage`;
- `POINT/LINE/CIRCLE/ARC → CadSketch`;
- preservation of canonical entities/dimensions/constraints/unresolved data;
- verified dimension extraction;
- canonical `dimension_id` verification key;
- canonical tolerance policy;
- canonical `CADPackage v1` builder;
- internal verification core aligned to v1;
- canonical `CADVerificationReport v1` builder;
- exact golden contract tests.

## 2. Какие исходные contracts использованы

- `SketchPackage`;
- `CADPackage`;
- `CADVerificationReport`;
- `CADVerificationItem`;
- `SketchDimension`;
- policies from `POLICIES_V1.md`.

## 3. Какие файлы изменены/добавлены

См. commit/PR данной итерации; изменения ограничены `chat_4_cad_bridge_verification/`.

## 4. Какие зависимости добавлены

Development only:

- `jsonschema==4.26.0`.

Runtime dependency `ezdxf==1.4.4` сохранена без изменений.

## 5. Какие тесты добавлены

- canonical fixture/schema loading;
- SketchPackage mapping;
- CADPackage exact golden;
- CADVerificationReport exact golden;
- unverified dimension exclusion from verification truth;
- unsupported entity reject;
- revised dimension-id based verification tests.

## 6. Какие тесты прошли

```text
Ran 14 tests
OK
```

## 7. Что не проверено

- real SOLIDWORKS import;
- COM connection;
- vendor constraint solving;
- vendor dimension read-back;
- Windows/SOLIDWORKS test host.

## 8. Известные ограничения

- vendor adapter отсутствует;
- artifact URI/storage создаётся внешним artifact/storage boundary;
- generic exporters не применяют CAD-native constraints;
- canonical v1 geometry ограничена POINT/LINE/CIRCLE/ARC.

## 9. Новые технические знания

- canonical verification identity — `dimension_id`;
- `measurement_id` nullable и используется для traceability;
- physical uncertainty не является CAD transfer tolerance;
- canonical transfer tolerance фиксирована policy;
- deterministic output сохраняет canonical dimension order.

## 10. Change Requests

`CHANGE_REQUEST_001_CAD_CONTRACT_BASELINE` — resolved/closed.

Новых Change Requests в этой итерации нет.

## 11. Что готово к интеграции

Готово:

```text
canonical SketchPackage fixture
→ Chat 4 mapper
→ internal CadSketch
→ SVG / DXF
→ verification engine
→ canonical CADVerificationReport
```

Не готово:

```text
SOLIDWORKS native adapter
→ native dimension/constraint creation
→ native read-back
```
