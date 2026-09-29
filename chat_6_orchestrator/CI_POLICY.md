# MREA CI Policy

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Effective from:** Pass 2  
**Expanded for Pass 3:** all currently executable slice boundaries + full `main` verification

## Purpose

CI is independent execution evidence. A worker chat's statement that tests passed is not sufficient for integration acceptance when GitHub Actions can execute the same checks on a clean runner.

## Canonical workflow

`.github/workflows/ci.yml`

The workflow runs on:

- pull requests targeting `main`;
- pushes to `main`;
- pushes to `chat-*/pass-*` worker branches;
- manual `workflow_dispatch`.

## Required slice jobs

- `Contracts / canonical fixtures`
- `Chat 1 / Capture`
- `Chat 2 / Measurement`
- `Chat 3 / Geometry`
- `Chat 4 / Generic CAD gate`
- `Chat 5 / Lifecycle`

## Required executable cross-slice jobs

- `Integration / Chat 1 -> Chat 2`
- `Integration / Chat 2 -> Chat 3`
- `Integration / Chat 3 -> Chat 4`
- `Integration / Chat 4 -> Chat 5`

Jobs may be conditionally skipped on unrelated worker branches to avoid making a slice red because of an unrelated boundary. On `main`, all four executable boundary gates run.

## Acceptance rule

A worker pass cannot be `ACCEPTED` for integration while a required CI job relevant to that pass is red.

After all accepted worker changes are integrated, the round cannot be declared `GREEN` until the full CI run on the assembled `main` is successful.

Possible exceptions must be explicitly documented by Chat 6 as environment-only gates, for example a real SOLIDWORKS runtime gate that cannot execute on a GitHub-hosted runner.

## Cross-slice policy

Slice-local green tests do not imply system compatibility.

Integration tests must exercise realistic producer output and consumer behavior, not only pre-normalized golden fixtures.

Current boundary intent:

### Chat 1 -> Chat 2

- real Chat 1 CapturePackage is built by Chat 1 code;
- clean-reference and measurement-frame IDs are consumed directly by Chat 2;
- Chat 2 must preserve evidence/reference IDs instead of inventing replacements;
- raw anchors remain `IMAGE_PX`.

### Chat 2 -> Chat 3

- real Chat 2 output contains `IMAGE_PX` anchors;
- a non-identity homography prevents accidental pass-through;
- Chat 3 must normalize to `MAT_XY_MM` while preserving measurement identity/value/provenance.

### Chat 3 -> Chat 4

- real Chat 3 code builds SketchPackage v1;
- Chat 4 consumes that produced package through its generic CAD transfer boundary;
- dimension/measurement traceability must survive read-back verification.

### Chat 4 -> Chat 5

- real generic Chat 4 CAD transfer and verification output is consumed by Chat 5;
- `VERIFIED` permits manufacturing eligibility;
- failed verification remains evidence but blocks manufacturing.

## Post-merge `main` gate

Every accepted merge triggers CI on `main`.

The final assembled `main` run is the authoritative software-integration evidence for round completion.

A previously green worker PR does not override a red final `main` run.

## SOLIDWORKS

Generic CAD mapping/export/verification remains in GitHub-hosted CI.

Real SOLIDWORKS 2026 COM integration requires a controlled Windows host with SOLIDWORKS installed. It is not considered verified by Linux/GitHub-hosted CI, protocol unit tests, C# source presence, or mock/test-double execution.

Until real-host evidence exists, status remains:

`UNVERIFIED`

## Branch protection target

`main` should be protected so pull requests cannot merge while required checks are failing.

Target required checks are the slice/contract jobs and executable integration jobs relevant to the merge candidate, excluding environment-only gates explicitly classified by Chat 6.
