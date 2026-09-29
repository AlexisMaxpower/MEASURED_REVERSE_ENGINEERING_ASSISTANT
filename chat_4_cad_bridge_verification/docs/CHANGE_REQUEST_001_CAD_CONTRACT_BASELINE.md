# CHANGE_REQUEST_001 — CAD Contract Baseline

**Requester:** Chat 4 — CAD Bridge & Verification  
**Дата:** 2026-09-29

## CHANGE_REQUEST

**Requester:** Chat 4  
**Contract:** `SketchPackage v1`, `CADVerificationReport v1`, связанная tolerance/units policy  
**Problem:** Chat 4 может реализовать внутренний CAD-neutral core, но не может корректно построить boundary mapper и contract tests без canonical schemas/fixtures. В repository отсутствуют утверждённые representation полей entities, dimensions, constraints, `measurement_id` mapping, verification report и tolerance policy.  
**Current behavior:** внутренний Chat 4 core не зависит от shared DTO. `ExpectedDimension` требует tolerance явно. SVG/DXF работают только от внутреннего `CadSketch`. Shared contracts не определяются локально.  
**Requested change:** Integrator должен опубликовать canonical v1 schemas и fixtures минимум для `SketchPackage` и `CADVerificationReport`, определить обязательный v1 entity subset, units policy и источник tolerance для CAD verification. Желательно также зафиксировать policy для unsupported entities/constraints и stable IDs.  
**Reason:** без этого mapper `SketchPackage → internal CadSketch` и mapper `internal VerificationReport → CADVerificationReport` потребовали бы угадывать shared contract, что нарушает ownership и SSOT.  
**Affected chats:** Integrator, Chat 3, Chat 4.  
**Backward compatible:** N/A — canonical v1 contract ещё не опубликован.  
**Migration:** не требуется для текущего Chat 4 internal core; после публикации schema добавляется boundary mapper без изменения internal exporter/verification APIs.

## Минимальные решения, требуемые от Integrator

1. `SketchPackage v1` schema + `sketch_package_v1.json` fixture.
2. `CADVerificationReport v1` schema + `cad_verification_v1.json` fixture.
3. Representation и stable ID rules для Point/Line/Circle/Arc/Polyline/ConstructionLine либо явно меньшего v1 subset.
4. Representation dimensions с обязательной связью `measurement_id`.
5. Units baseline и conversion policy.
6. Tolerance source/policy для `VERIFIED`.
7. Representation `MISMATCH`, `MISSING`, `CONSTRAINT_CONFLICT` в report contract.
8. Policy для unsupported entity/constraint: reject / unresolved / warning.
