# ORCHESTRATOR DIRECTIVE — Chat 1
**Revision:** OD-2026-09-29-002  
**Owner:** Chat 6
**Pass:** 2  
**Branch:** `chat-1/pass-2`

Read before coding.

## Accepted from Pass 1
Canonical `ProjectContract v1` / `CapturePackage v1` boundary and the ChArUco calibration baseline are accepted.

## Pass 2 priority
Produce a deterministic perspective-normalized derived reference artifact for one calibrated FRONT view.

Requirements:
- use existing calibration/homography;
- do not replace the original clean-reference artifact;
- preserve explicit source → derived provenance;
- preserve pixel dimensions/media metadata;
- do not invent metric truth from the warp itself;
- keep canonical CapturePackage backward compatible unless a Change Request is approved.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/project_v1.json`
- `tests/fixtures/contracts/capture_package_v1.json`

## CI requirement
Push Pass 2 work only to `chat-1/pass-2`. GitHub Actions in `.github/workflows/ci.yml` must remain green for Chat 1 and shared contract checks. Record CI status in `ORCHESTRATOR_HANDOFF.md`.

## Acceptance target
Synthetic non-identity perspective case produces a deterministic normalized image artifact, while the original evidence image remains addressable and canonical package serialization remains schema-valid.

## Do not
- modify `core/contracts` or canonical fixtures;
- move measurement semantics into Capture;
- overwrite evidence images;
- commit Pass 2 implementation directly to `main`.

## Handoff
Finish Pass 2 with `ORCHESTRATOR_HANDOFF.md` per `chat_6_orchestrator/DEVELOPMENT_WORKFLOW.md`.
