import unittest

from mrea_cad_bridge import ExpectedDimension, VerificationEngine, VerificationStatus


class VerificationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = VerificationEngine()

    def test_verified_within_explicit_tolerance(self) -> None:
        report = self.engine.verify(
            expected=(ExpectedDimension("M001", 42.18, 0.01),),
            actual_values_mm={"M001": 42.180},
        )
        result = report.results[0]
        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertAlmostEqual(result.delta_mm or 0.0, 0.0)

    def test_mismatch_is_not_silently_corrected(self) -> None:
        report = self.engine.verify(
            expected=(ExpectedDimension("M001", 5.18, 0.01),),
            actual_values_mm={"M001": 5.31},
        )
        result = report.results[0]
        self.assertEqual(result.status, VerificationStatus.MISMATCH)
        self.assertEqual(result.expected_value_mm, 5.18)
        self.assertEqual(result.actual_value_mm, 5.31)

    def test_missing_dimension(self) -> None:
        report = self.engine.verify(
            expected=(ExpectedDimension("M002", 76.40, 0.01),),
            actual_values_mm={},
        )
        self.assertEqual(report.results[0].status, VerificationStatus.MISSING)
        self.assertIsNone(report.results[0].actual_value_mm)

    def test_constraint_conflict_has_priority(self) -> None:
        report = self.engine.verify(
            expected=(ExpectedDimension("M003", 60.00, 0.01),),
            actual_values_mm={"M003": 60.0},
            constraint_conflicts={"M003"},
        )
        self.assertEqual(report.results[0].status, VerificationStatus.CONSTRAINT_CONFLICT)

    def test_output_order_is_deterministic(self) -> None:
        report = self.engine.verify(
            expected=(
                ExpectedDimension("M002", 2.0, 0.01),
                ExpectedDimension("M001", 1.0, 0.01),
            ),
            actual_values_mm={"M001": 1.0, "M002": 2.0},
        )
        self.assertEqual([item.measurement_id for item in report.results], ["M001", "M002"])

    def test_duplicate_expected_measurement_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.verify(
                expected=(
                    ExpectedDimension("M001", 1.0, 0.01),
                    ExpectedDimension("M001", 1.0, 0.01),
                ),
                actual_values_mm={"M001": 1.0},
            )


if __name__ == "__main__":
    unittest.main()
