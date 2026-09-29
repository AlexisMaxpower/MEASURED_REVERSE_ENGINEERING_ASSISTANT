# ORCHESTRATOR DIRECTIVE — Chat 2
**Revision:** OD-2026-09-29-001  
**Owner:** Chat 6

Read before the next coding iteration.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`

## Current directive
Phase A dataclasses remain valid internal models. Add a shared-boundary serializer/adapter to canonical:
- `FeatureAnchor`;
- `PhysicalMeasurement`;
- `MeasurementPackage`.

Canonical v1 anchors may use `IMAGE_PX` or `MAT_XY_MM`. Preserve evidence and provenance.

## Next acceptance target
Load canonical CapturePackage fixture, create at least one manual verified measurement and serialize a schema-valid MeasurementPackage.

## Do not
- redefine shared provenance at the wire boundary;
- let OCR/voice become verified without explicit confirmation policy;
- edit shared contracts directly.
