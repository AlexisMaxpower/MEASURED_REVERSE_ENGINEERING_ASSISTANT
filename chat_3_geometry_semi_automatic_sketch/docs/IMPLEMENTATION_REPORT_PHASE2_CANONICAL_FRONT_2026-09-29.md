# Chat 3 — Implementation Report — Phase 2 Canonical FRONT

**Дата:** 2026-09-29  
**Directive:** `OD-2026-09-29-001`  
**Repository:** `AlexisMaxpower/MEASURED_REVERSE_ENGINEERING_ASSISTANT`  
**Branch:** `main`

## 1. Implemented

- canonical `CapturePackage v1` + `MeasurementPackage v1` input adapter;
- cross-package project/part/capture linkage checks;
- mandatory `MAT_XY_MM` enforcement for v1 FRONT baseline;
- canonical measurement anchors converted to internal `AnchorRef`;
- `feature_id` preserved as semantic binding hint;
- mandatory v1 `POINT` primitive support added;
- `GeometryGraph` updated for point incidence;
- `AnchorEntityMatcher` now resolves exact `feature_id` before coordinate fallback;
- `DimensionBinding` now retains `measurement_type`;
- canonical `SketchPackageBuilder` implemented without redefining Integrator schema;
- deterministic canonical entity ordering;
- deterministic canonical dimension ordering;
- canonical dimension type mapping;
- verified `measurement_id` propagation;
- internal unresolved/conflicts projected to canonical `unresolved`;
- purely inferred constraints remain internal in this phase and are not published as canonical constraints;
- canonical FRONT primitive detector-output fixture added;
- exact golden test against `/tests/fixtures/contracts/sketch_package_v1.json` added;
- Draft 2020-12 schema validation test added;
- primitive-order determinism test added;
- canonical measurement-link preservation test added;
- canonical `POINT` schema test added.

## 2. Source contracts

Consumed from Integrator:

- `/core/contracts/mrea_contracts_v1.schema.json`;
- `/core/contracts/POLICIES_V1.md`;
- `/tests/fixtures/contracts/capture_package_v1.json`;
- `/tests/fixtures/contracts/measurement_package_v1.json`.

Expected canonical output fixture:

- `/tests/fixtures/contracts/sketch_package_v1.json`.

No shared contract file was modified by Chat 3.

## 3. Changed / added files

### Runtime

- `src/mrea_geometry/models.py`;
- `src/mrea_geometry/graph.py`;
- `src/mrea_geometry/core.py`;
- `src/mrea_geometry/contracts.py`;
- `src/mrea_geometry/sketch_package.py`;
- `src/mrea_geometry/__init__.py`.

### Tests / fixtures

- `tests/fixtures/internal/front_golden_primitives.json`;
- `tests/test_canonical_front_pipeline.py`;
- `pyproject.toml`.

### Documentation

- `docs/BUILD_REUSE_CHECK_PHASE2_CANONICAL_BRIDGE.md`;
- `docs/IMPLEMENTATION_REPORT_PHASE2_CANONICAL_FRONT_2026-09-29.md`;
- `docs/IMPLEMENTATION_STATE.md` updated separately.

## 4. Dependencies

Test-only:

- `pytest >=8,<9`;
- `jsonschema >=4.23,<5`.

Production geometry core has no new third-party runtime dependency.

## 5. Tests added

Canonical Phase 2 suite adds four acceptance tests:

1. canonical FRONT output equals Integrator golden fixture exactly;
2. primitive input order does not change canonical output;
3. all four verified dimensions preserve canonical `measurement_id` links;
4. `POINT` serializes as a schema-valid v1 entity.

Existing Phase 1 suite remains in place.

## 6. Tests passed

### Previously verified Phase 1

Historical exact-payload run recorded:

```text
6 passed in 0.06s
```

### Phase 2 current environment

Not executed against repository checkout in this ChatGPT environment.

Reason: container DNS cannot resolve `github.com`, so a fresh clone/install/test run cannot be performed. Repository does not currently contain a GitHub Actions workflow that Chat 3 can use without changing global repository infrastructure.

The Phase 2 acceptance suite has been statically cross-checked against the current canonical schema/fixtures, but this is not reported as a runtime pass.

## 7. Not verified

- actual `pytest` result for Phase 2 files;
- package installation on a clean workstation;
- raw image/OpenCV primitive extraction;
- non-FRONT views;
- IMAGE_PX → MAT_XY_MM conversion;
- advanced constraint promotion/resolution;
- CAD import/read-back.

## 8. Limitations

- `front_golden_primitives.json` represents deterministic detector output; it is not produced from the `fixture://images/front_clean.png` image because no image artifact exists in the repository fixture set;
- Phase 2 publishes no inferred constraints into canonical output, matching the current golden fixture;
- canonical linear dimension entity selection is intentionally minimal for the FRONT baseline;
- only measurements already expressed in `MAT_XY_MM` are accepted by the canonical adapter.

## 9. New technical knowledge

The Integrator baseline resolves the previous assumption that Chat 2 anchors are necessarily pixel-only. Canonical `MeasurementPackage v1` can already carry anchors in `MAT_XY_MM` plus `feature_id`, enabling deterministic semantic binding without a pixel transform in the golden FRONT case.

The expected CAD-oriented dimension binding is not always identical to the two boundary features measured physically. Example: width anchors identify left/right edges, while canonical `D-WIDTH` attaches to `L-BOTTOM`. The builder therefore distinguishes measurement-association entities from canonical dimension-host entities.

## 10. Change Requests

None required for the current v1 FRONT acceptance target.

Future Change Request may be required for:

- constraint promotion policy;
- IMAGE_PX anchor conversion contract;
- multi-view geometry;
- v1 vocabulary expansion beyond POINT/LINE/CIRCLE/ARC.

## 11. Ready for integration

Code and tests are committed in the Chat 3 ownership area and are ready for Integrator review.

Release-gate status remains **runtime verification pending** until Phase 2 tests are executed in an environment with the repository checkout and test dependencies.
