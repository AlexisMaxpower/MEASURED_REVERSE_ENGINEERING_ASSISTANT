# ORCHESTRATOR DIRECTIVE — Chat 3
**Revision:** OD-2026-09-29-003  
**Owner:** Chat 6  
**Pass:** 3  
**Branch:** `chat-3/pass-3`

## Accepted baseline
Pass 2 is `ACCEPTED`. The Round 1 `IMAGE_PX -> MAT_XY_MM` blocker is closed and independently green in CI. A real repository-level `Chat 3 -> Chat 4` producer-consumer gate is now canonical CI.

## Pass 3 priority
Begin real **semi-automatic geometry candidate extraction** from normalized/reference imagery.

Required:
- deterministic candidate extraction for v1 primitives: LINE, CIRCLE and ARC where reliable for chosen fixture; POINT/endpoints may be derived as needed;
- prefer OpenCV/established geometry libraries over reimplementing generic algorithms;
- all image-derived primitives must carry truthful non-measured provenance such as `VISION_DETECTED`;
- bind verified physical measurements to detected geometry without changing verified values;
- ambiguous/unsupported candidates remain explicit/unresolved;
- output remains deterministic `SketchPackage v1`;
- add stable image fixtures and golden geometry tests.

## Canonical integration gates
Your pass must keep green:
- `Chat 3 / Geometry`;
- `Integration / Chat 2 -> Chat 3`;
- `Integration / Chat 3 -> Chat 4`;
- shared contract checks.

## Do not
- infer hidden geometry as fact;
- weaken measurement truth hierarchy;
- add CAD-vendor logic;
- modify Chat-6-owned CI/shared integration tests;
- change canonical contracts without approved CR;
- commit directly to `main`.

## Process
Work only in `chat-3/pass-3`.

Finish with `ORCHESTRATOR_HANDOFF.md`. **Handoff freezes the branch.** No post-handoff commits until Chat 6 explicitly returns `FIX_REQUIRED`.

See `chat_6_orchestrator/PASS_3_PLAN_2026-09-29.md` and `DEVELOPMENT_WORKFLOW.md`.
