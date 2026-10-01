from __future__ import annotations

from pathlib import Path
import unittest


TRANSFER_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "solidworks_agent"
    / "SolidWorksTransfer.cs"
).read_text(encoding="utf-8")


class SolidWorksDrivenDimensionConflictEmissionTests(unittest.TestCase):
    def test_driven_dimension_status_is_normalized_to_dimension_conflict(self) -> None:
        driven_check = (
            "if (setStatus == (int)swSetValueReturnStatus_e.swSetValue_DrivenDimension)"
        )
        add_conflict = "constraintConflicts.Add(dimension.dimension_id);"
        generic_failure = (
            "else if (setStatus != (int)swSetValueReturnStatus_e.swSetValue_Successful)"
        )

        self.assertIn("var constraintConflicts = new List<string>();", TRANSFER_SOURCE)
        self.assertIn(driven_check, TRANSFER_SOURCE)
        self.assertIn(add_conflict, TRANSFER_SOURCE)
        self.assertIn(generic_failure, TRANSFER_SOURCE)
        self.assertLess(TRANSFER_SOURCE.index(driven_check), TRANSFER_SOURCE.index(generic_failure))
        self.assertIn("constraint_conflicts = constraintConflicts", TRANSFER_SOURCE)

    def test_non_driven_set_value_failures_remain_hard_failures(self) -> None:
        self.assertIn(
            'throw new InvalidOperationException(\n'
            '                        "Failed to set dimension " + dimension.dimension_id + "; SetSystemValue3 status=" + setStatus);',
            TRANSFER_SOURCE,
        )

    def test_relation_over_definition_is_not_reclassified_as_dimension_conflict(self) -> None:
        self.assertIn(
            'throw new InvalidOperationException(\n'
            '                            "Constraint caused an over-defining sketch: " + constraint.constraint_id);',
            TRANSFER_SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
