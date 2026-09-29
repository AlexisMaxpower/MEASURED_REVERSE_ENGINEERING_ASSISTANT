# MREA Shared Contract Policies v1

## Stable IDs
Wire-level IDs are opaque strings. Producers should normally use UUIDs, but consumers must not parse semantic meaning from IDs.

## Coordinates
- `IMAGE_PX`: reference-image pixel coordinates.
- `MAT_XY_MM`: rectified Measurement Mat coordinates in millimetres.
- `SketchPackage v1` uses `MAT_XY_MM`.

## Measurement truth
A verified physical measurement is never overwritten by image geometry. Conflicts are explicit.

## Uncertainty vs CAD transfer tolerance
`uncertainty` describes uncertainty of the physical measurement. It does not excuse a CAD import mismatch.

CAD verification tests numerical transfer into CAD, not manufacturing tolerance.

Baseline:
- length: `1e-6 mm`;
- angle: `1e-6 deg`.

## Sketch v1 subset
Mandatory:
- POINT
- LINE
- CIRCLE
- ARC

Other geometry stays explicit in `unresolved`.

## Determinism
Identical canonical fixture input must produce deterministic canonical output within golden tests.
