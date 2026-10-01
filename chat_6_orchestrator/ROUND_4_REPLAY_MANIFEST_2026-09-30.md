# MREA — Round 4 Replay Manifest

**Owner:** Chat 6  
**Directive:** `OD-2026-09-30-004`  
**Purpose:** authoritative Stage-1 replay input for Deputy 1

## Base

Stage-1 validation base `main`:

`0480787951938e5ca4c24f569beae204c1aae432`

Stage-1 validation branch:

`integration/pass-4-stage1-replay-candidate`

Validation commit:

`0a46ebb27abd3267e46afaf86b50383ab6b7d5a0`

Validation tree:

`d1fd50f49dd041e4b2be383be330f9a30255b43a`

Validation CI:

`36726156911` — `SUCCESS`

## Frozen worker provenance

| Slice | Frozen worker handoff | Implementation snapshot used |
|---|---|---|
| Chat 1 | `a7d607f8cdd281749ae40529de15c2d84dfda78e` | `1bd52e0a6c339e8f68fbae4d9005c8df86824e31` |
| Chat 2 | `539d58567046fd29ccf2d42b629227ffe8da6546` | `b5f7a85c66a0c72aa41edd1b045fa5a9f474b9e7` |
| Chat 3 | `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49` | `1a6b58e6e87786b8e67e6f8525ece98e588dfad3` |
| Chat 4 | `61f37a4dd46921b7fe9145bcbe5242bc3f6417b3` | `d9633e3b8e95158d359e502e9797d4876384cd09` |
| Chat 5 | `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f` | `1b45f9a2b815ff4a150dd9a49d21dde4abdde9df` |

## Stage-1 replay composition

The validation tree overlaid only worker-owned slice content onto current main.

### Chat 1

- `chat_1_project_guided_capture/README.md` -> blob `b2a737519ebe6a828a1644cc5e4d90a50d8ba23e`
- `chat_1_project_guided_capture/docs` -> tree `188027ab9871f4399875b0357a9545fa0fa4f7c4`
- `chat_1_project_guided_capture/src` -> tree `83e2fc74adbeedd5d2c927b24754490259c3ce5c`
- `chat_1_project_guided_capture/tests` -> tree `fd0000fd08c2b4ebd6bbfa6d40cc3cbbdb2425b0`

### Chat 2

- `chat_2_physical_measurement/README.md` -> blob `1b55d707e5a8984d8490944116bb8ae23fa4742d`
- `chat_2_physical_measurement/docs` -> tree `5d9323df35ae6d4b5b0db0028f0501d55bb3a443`
- `chat_2_physical_measurement/src` -> tree `3372aa1bd2443277df762f5a8a8756b5d0b00501`
- `chat_2_physical_measurement/tests` -> tree `163875f42a3cfa9b6ffeec369a451fe55a2f4afa`

### Chat 3

- `chat_3_geometry_semi_automatic_sketch/docs` -> tree `4445ed700864d310d940a9a6fcee3da7f96ecb75`
- `chat_3_geometry_semi_automatic_sketch/pyproject.toml` -> blob `1cd9c8ec802c695f9e78b67229188c04814b772c`
- `chat_3_geometry_semi_automatic_sketch/src` -> tree `29127c20d71c6f45821501e53394a99af7b0a517`
- `chat_3_geometry_semi_automatic_sketch/tests` -> tree `bbd94c598bf2eb5d337668966927bf6869b4a9d9`

### Chat 4

- `chat_4_cad_bridge_verification/docs` -> tree `047f615c7b3bf47eca7001904895ffb0793075fd`
- `chat_4_cad_bridge_verification/solidworks_agent` -> tree `042e07e73998c1159584a4e0b63e43dd01c4fe31`
- `chat_4_cad_bridge_verification/src` -> tree `0a7ca5a1d36bfc1cc82a083c093ce5730e85d903`
- `chat_4_cad_bridge_verification/tests` -> tree `82bacd93eaefd41a54d7ede3c4f2bfd8f512384d`

### Chat 5

- `chat_5_lifecycle_engineering_knowledge/README.md` -> blob `1390fc33de840ec1cf1fb127b7792b358821a164`
- `chat_5_lifecycle_engineering_knowledge/docs` -> tree `64f714353ed17fee17bfee73841fc44cf6e2c607`
- `chat_5_lifecycle_engineering_knowledge/src` -> tree `e98501d47459b48f9dafe1e6cefcecc93ffa7517`
- `chat_5_lifecycle_engineering_knowledge/tests` -> tree `21db02689124fc05c9e21b6aa66925843c716f5c`

## Deliberately excluded from worker replay

Deputy 1 must preserve the then-current `main` versions of:

- `.github/workflows/**`;
- `core/contracts/**`;
- `tests/fixtures/contracts/**`;
- `tests/integration/**` owned by Chat 6;
- all worker `ORCHESTRATOR_DIRECTIVE.md` files;
- worker `ORCHESTRATOR_HANDOFF.md` files as integration inputs rather than product replacements;
- Chat-6/7/8 orchestration documents except new Stage-2 evidence created by the responsible deputy.

No blind worker-history merge is authorized.

## Validation result

Run `36726156911` on commit `0a46ebb27abd3267e46afaf86b50383ab6b7d5a0` executed and passed:

- Contracts / canonical fixtures;
- Chat 1 / Capture;
- Chat 2 / Measurement;
- Chat 3 / Geometry;
- Chat 4 / Generic CAD gate;
- Chat 5 / Lifecycle;
- Chat 1 -> Chat 2;
- Chat 2 -> Chat 3;
- Chat 3 -> Chat 4;
- Chat 4 -> Chat 5;
- golden path.

## Deputy-1 requirement

This manifest is Stage-1 evidence, not a substitute for independent Deputy-1 review.

Deputy 1 must construct the official `integration/pass-4-candidate` from the then-current `main`, independently compare the accepted worker content and preserve current shared infrastructure. The final official candidate must reproduce the accepted semantics and obtain its own full CI evidence before handoff to Chat 8.
