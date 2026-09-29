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

Repository test inventory after Pass 2 boundary tests: **32 tests** (23 baseline + 9 SOLIDWORKS-agent boundary tests).

Pass 2 sandbox execution: **27 tests, OK** — exporters (3) + verification (6) + existing adapter/pipeline (9) + SOLIDWORKS-agent boundary (9). Пять schema contract tests не перезапускались в локальном staging, поскольку shared schema не материализован в sandbox checkout; shared schema/tests Pass 2 не изменяет. Real Windows/SOLIDWORKS execution: **UNVERIFIED**.

## Pass 2 — SOLIDWORKS 2026 CAD Agent

По `OD-2026-09-29-002` и ADR-001 добавлен реальный vendor path:

```text
SketchPackage v1
→ SolidWorksAgentAdapter (Python)
→ slice-local JSON process protocol
→ Mrea.SolidWorksCadAgent.exe (.NET Framework 4.8 x64, STA)
→ SOLIDWORKS 2026 COM/API
→ normalized bindings/read-back/artifact
→ existing VerificationEngine
→ CADPackage v1 + CADVerificationReport v1
```

Реализованы preflight unresolved/unsupported checks, out-of-process runner, C# agent skeleton/transfer path, native `.SLDPRT` artifact registration and real-host smoke scripts. `CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` resolved by `chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`.

Текущий real-host status: **UNVERIFIED** — финальная проверка требует Windows 11 x64 + SOLIDWORKS 2026 x64. См. `docs/SOLIDWORKS_2026_SMOKE_TEST.md`.

Current real-host slice deliberately supports golden LINE/CIRCLE + DISTANCE/DIAMETER (RADIUS path included). POINT/ARC/ANGLE and canonical constraints are explicit follow-up work and are not silently approximated.

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
