# MREA Canonical Shared Contracts

**Owner:** Chat 6 / Integrator  
**Baseline:** `mrea.contracts.v1`

This directory is the canonical cross-slice boundary. Slice-local dataclasses/Pydantic models are implementation details until serialized through these schemas.

## Canonical schema
`mrea_contracts_v1.schema.json` contains JSON Schema `$defs` for:
- ProjectContract
- ArtifactReference
- MeasurementCaptureFrame
- CapturePackage
- FeatureAnchor
- PhysicalMeasurement
- MeasurementPackage
- SketchPackage
- CADPackage
- CADVerificationReport
- LifecycleEvent

## Policies
- IDs are opaque, non-empty strings. UUID is recommended, not required.
- Timestamps use RFC3339 and should be UTC.
- v1 length unit is `mm`; angle unit is `deg`.
- Verified measurement value is authoritative over vision-derived estimates.
- Physical measurement uncertainty and CAD transfer tolerance are different concepts.
- CAD transfer default tolerance is `1e-6` in the reported unit.
- Sketch v1 mandatory entities: POINT, LINE, CIRCLE, ARC.
- Unknown/unsupported geometry belongs in `unresolved`.

## Fixtures
Canonical fixtures live in `tests/fixtures/contracts/`.

## Change policy
Backward-incompatible changes require a Change Request approved by Chat 6 and a schema-version increment.
