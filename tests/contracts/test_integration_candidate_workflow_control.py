from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/round4_truth.yml"


def test_truth_workflow_accepts_versioned_integration_candidate_branches() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "- integration/pass-*-candidate" in text
    assert "startsWith(github.ref, 'refs/heads/integration/pass-')" in text
    assert "endsWith(github.ref, '-candidate')" in text
    assert "startsWith(github.head_ref, 'integration/pass-')" in text
    assert "endsWith(github.head_ref, '-candidate')" in text
    assert "integration/pass-4-candidate" not in text
