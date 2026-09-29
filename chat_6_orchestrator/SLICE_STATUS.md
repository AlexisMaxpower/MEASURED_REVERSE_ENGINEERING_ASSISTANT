# Slice Status

| Slice | Round 1 verdict | Pass 2 integration gate |
|---|---|---|
| Chat 1 | ACCEPTED | perspective-normalized derived reference + Chat 1 CI green |
| Chat 2 | ACCEPTED AS SLICE | truthful IMAGE_PX/evidence boundary + Chat 2 CI green |
| Chat 3 | FIX REQUIRED FOR INTEGRATION | real IMAGE_PX → MAT_XY_MM cross-slice CI gate green |
| Chat 4 | ACCEPTED FOR GENERIC CAD GATE | generic CAD CI green + SOLIDWORKS adapter scaffold per ADR-001 |
| Chat 5 | ACCEPTED WITH PROCESS FIX | CAD-verification eligibility policy + Chat 5 CI green + handoff |

## Pass 2 branch policy

- `chat-1/pass-2`
- `chat-2/pass-2`
- `chat-3/pass-2`
- `chat-4/pass-2`
- `chat-5/pass-2`

Worker implementation does not land directly in `main`.

## Required automation

Canonical CI: `.github/workflows/ci.yml`

Current required cross-slice gate:

`tests/integration/test_chat2_to_chat3_boundary.py`

The integration gate intentionally fails against the uncorrected Round 1 Chat 3 adapter and becomes green only after proper calibration-based normalization is implemented.

This file is a snapshot; current repository/branch state and Chat 6 review remain authoritative.
