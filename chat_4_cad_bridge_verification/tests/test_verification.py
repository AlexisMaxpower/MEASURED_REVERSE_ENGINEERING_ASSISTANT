import unittest

from mrea_cad_bridge import ExpectedDimension, VerificationEngine, VerificationStatus


class VerificationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = VerificationEngine()

    def expected(self, dimension_id: str, value: float = 42.18, unit: str = "mm"):
        return ExpectedDimension(
            dimension_id=dimension_id,
            measurement_id=f"M-{dimension_id}",
            expected_value=value,
            unit=unit,
            tolerance=1e-6,
        )

    def test_verified_within_canonical_transfer_tolerance(self) -> None:
        report = self.engine.verify(
            expected=(self.expected("D001"),),
            actual_values={"D001": 42.1800005},
        )
        result = report.results[0]
        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertAlmostEqual(result.difference or 0.0, 0.0000005)

    def test_mismatch_is_not_silently_corrected(self) -> None:
        report = self.engine.verify(
            expected=(self.expected("D001", 5.18),),
            actual_values={"D001": 5.31},
        )
        result = report.results[0]
        self.assertEqual(result.status, VerificationStatus.MISMATCH)
        self.assertEqual(result.expected_value, 5.18)
        self.assertEqual(result.actual_value, 5.31)
        self.assertAlmostEqual(result.difference or 0.0, 0.13)

    def test_missing_dimension(self) -> None:
        report = self.engine.verify(
            expected=(self.expected("D002", 76.40),),
            actual_values={},
        )
        self.assertEqual(report.results[0].status, VerificationStatus.MISSING)
        self.assertIsNone(report.results[0].actual_value)

    def test_constraint_conflict_has_priority(self) -> None:
        report = self.engine.verify(
            expected=(self.expected("D003", 60.00),),
            actual_values={"D003": 60.0},
            constraint_conflicts={"D003"},
        )
        self.assertEqual(report.results[0].status, VerificationStatus.CONSTRAINT_CONFLICT)

    def test_input_order_is_preserved_for_canonical_determinism(self) -> None:
        report = self.engine.verify(
            expected=(self.expected("D-WIDTH", 80.2), self.expected("D-HEIGHT", 42.1)),
            actual_values={"D-WIDTH": 80.2, "D-HEIGHT": 42.1},
        )
        self.assertEqual([item.dimension_id for item in report.results], ["D-WIDTH", "D-HEIGHT"])

    def test_duplicate_expected_dimension_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.verify(
                expected=(self.expected("D001", 1.0), self.expected("D001", 1.0)),
                actual_values={"D001": 1.0},
            )


if __name__ == "__main__":
    unittest.main()
