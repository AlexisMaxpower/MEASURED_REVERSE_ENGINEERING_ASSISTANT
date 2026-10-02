# Chat 2 — Physical Measurement

Эта директория — рабочая область Chat 2 проекта MREA.

## Ownership

Chat 2 отвечает за vertical slice `Physical Measurement`:

- `MeasurementSession`;
- measurement types;
- annotation UX;
- feature anchor selection and snapping;
- OCR pipeline;
- voice value;
- user confirmation;
- caliper detection research;
- jaw/contact estimation;
- evidence and provenance;
- `MeasurementPackage` construction.

Chat 2 не владеет shared contracts и не изменяет их без Change Request для Integrator.

## Coordination authority

Перед новым проходом Chat 2 читает:

1. актуальный shared `main`;
2. `ORCHESTRATOR_DIRECTIVE.md`;
3. `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
4. `core/contracts/mrea_contracts_v1.schema.json`;
5. `core/contracts/POLICIES_V1.md`;
6. canonical fixtures и repository-owned CI.

При конфликте локальной документации с canonical contract / orchestration state приоритет имеет общий repository source of truth.

Текущая worker directive на старте Pass 18: `OD-2026-10-02-010`.

## Main implementation surfaces

- `src/physical_measurement/models.py` — internal measurement domain;
- `src/physical_measurement/service.py` — MeasurementSession application service;
- `src/physical_measurement/repository.py` — in-memory + durable SQLite session persistence and pagination;
- `src/physical_measurement/hands_free.py` — provider-independent voice/candidate state machine;
- `src/physical_measurement/recovery.py` — fail-closed durable hands-free restart recovery;
- `src/physical_measurement/anchor_selection.py` — provider-independent manual-pick / snap proposal / explicit-accept workflow;
- `src/physical_measurement/type_registry.py` — measurement-type semantics;
- `src/physical_measurement/boundary.py` — internal measurement → canonical `MeasurementPackage` adapter.

## Accepted baseline through Round 17

The accepted `main` before Pass 18 already contains:

- Phase-A manual measurement baseline;
- raw `IMAGE_PX` canonical measurement output;
- complete measurement type registry / anchor cardinality checks;
- unit-neutral uncertainty handling;
- provider-independent voice/OCR/device candidate state machine;
- explicit confirm / reject / correct behavior;
- deterministic Russian spoken measurement parsing and unit checks;
- durable SQLite measurement sessions;
- deterministic enumeration and keyset pagination;
- durable hands-free restart recovery for exact-context unverified candidates.

## Pass 18 — Phase-B anchor snapping

Pass 18 adds the first provider-independent snapping policy.

```text
manual IMAGE_PX pick
+ VISION_DETECTED target candidates
→ same-view/reference filtering
→ radius filtering
→ unique nearest proposal OR fail closed
→ explicit user accept OR keep raw
→ FeatureAnchor placement
```

Important truth boundary:

- a detector output is only a proposal;
- equal-distance alternatives are not silently tie-broken;
- accepted snap keeps `VISION_DETECTED` source and records `USER_CONFIRMED` separately;
- keep-raw remains `MANUAL_MEASURED`;
- measurement verification semantics are unchanged;
- shared contracts are unchanged.

The current `FeatureAnchor` persistence model does not yet contain durable snap-selection provenance. `FeatureAnchorSelection` therefore carries that metadata in the application layer until a dedicated durable-anchor metadata migration is approved.

## Truth / provenance invariants

1. Voice/OCR/device output is a candidate, not a verified fact.
2. Physical measurement verification requires explicit user confirmation.
3. Rejected candidates do not remain active measurement truth.
4. Correction creates a new candidate ID and never inherits verified state.
5. `VISION_DETECTED`, `AI_INFERRED` and derived provenance are not accepted as direct physical-measurement values.
6. Snapping may advise anchor placement but may not silently create an accepted anchor.
7. Evidence/reference/view linkage is preserved.
8. Raw measurement anchors remain `IMAGE_PX`; `IMAGE_PX -> MAT_XY_MM` belongs downstream.
9. Durable session decoding/enumeration/recovery remains fail-closed.

## Worker delivery rule

- start from current shared `main`;
- use a new pass branch;
- stay inside Chat-2 ownership;
- run Chat-2 plus adjacent contract/boundary gates;
- publish exact implementation SHA / CI evidence;
- record `ORCHESTRATOR_HANDOFF.md` last;
- do not merge directly to `main`.
