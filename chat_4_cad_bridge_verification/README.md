# Chat 4 — CAD Bridge & Verification

Эта директория является изолированной рабочей областью Chat 4 проекта MREA.

## Ownership

Chat 4 отвечает за vertical slice `CAD Bridge & Verification`:

- canonical `SketchPackage` intake;
- SVG/DXF export;
- `CADPackage`;
- vendor-neutral CAD adapter/read-back boundary;
- SOLIDWORKS adapter;
- создание CAD sketch/entities/dimensions/constraints;
- сохранение связи CAD dimensions с `dimension_id` и `measurement_id`;
- CAD read-back;
- `CADVerificationReport`;
- CAD integration tests.

Chat 4 не владеет capture, measurement extraction, geometry semantics, lifecycle или shared contracts.

## Source of truth

Для cross-slice boundary используются только:

- `../core/contracts/mrea_contracts_v1.schema.json`;
- `../core/contracts/POLICIES_V1.md`;
- `../tests/fixtures/contracts/`;
- `ORCHESTRATOR_DIRECTIVE.md`.

Slice-local models являются implementation details.

## Реализованный baseline

```text
SketchPackage v1
    ↓ canonical mapper
MappedSketchPackage
    ├─ internal CadSketch
    └─ verified dimensions
          ↓
      CadAdapter
          ↓
CadDimensionBinding + normalized CadReadBack
          ↓ identity / traceability / unit validation
      VerificationEngine
          ↓
internal VerificationReport
          ↓ canonical mapper
CADPackage v1 + CADVerificationReport v1
```

Generic layer:

- deterministic SVG exporter;
- DXF R12 exporter via `ezdxf`;
- canonical `CADPackage v1` builder;
- canonical `CADVerificationReport v1` builder;
- vendor-neutral `CadAdapter` protocol;
- explicit `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` mapping;
- normalized CAD read-back in `mm` / `deg`;
- deterministic `TestDoubleCadAdapter`;
- full canonical golden flow without installed SOLIDWORKS;
- adapter identity, binding identity, `measurement_id` traceability and unit-drift guards;
- no-silent-correction verification statuses.

## Dependencies

Runtime:

```text
ezdxf==1.4.4
```

Development / contract tests:

```text
jsonschema==4.26.0
```

## Проверка

Из `chat_4_cad_bridge_verification/`:

```text
pip install -r requirements-dev.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

Repository test inventory after hardening: **23 tests**.

Последний clean repository baseline до adapter work: **14 tests, OK**. В reconstructed local harness выполнены exporters + verification + все 9 adapter/pipeline tests: **18 tests, OK**. Пять schema contract tests не перезапускались в текущем container из-за отсутствия outbound GitHub DNS; shared schema/contract tests этим patch не изменяются.

## Текущий следующий этап

Generic CAD gate закрыт. Следующий vendor-specific этап — SOLIDWORKS C#/.NET/COM adapter за существующим normalized boundary.

Открыт `docs/CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md`; требуется canonical решение Chat 6 по:

- supported SOLIDWORKS version;
- .NET target;
- interop strategy;
- Windows/SOLIDWORKS test host.

## Главный инвариант

Verified physical value не корректируется по CAD read-back.

Допустимые item statuses:

- `VERIFIED`;
- `MISMATCH`;
- `MISSING`;
- `CONSTRAINT_CONFLICT`.

Canonical `overall_status`:

- `VERIFIED`;
- `FAILED`.
