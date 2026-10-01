from __future__ import annotations

import unittest

from mrea_cad_bridge import (
    CadAdapterError,
    CadAdapterResult,
    CadReadBack,
    parse_solidworks_agent_response,
)


def artifact(**overrides):
    value = {
        "artifact_id": "ART-001",
        "kind": "CAD_NATIVE",
        "uri": "file:///tmp/part.bin",
        "media_type": "application/octet-stream",
        "sha256": "abc123",
        "metadata": {"source": "test"},
    }
    value.update(overrides)
    return value


def adapter_result(*artifacts):
    return CadAdapterResult(
        adapter_name="TEST_ADAPTER",
        bindings=(),
        read_back=CadReadBack(dimensions=()),
        artifacts=tuple(artifacts),
    )


class AdapterArtifactBoundaryTests(unittest.TestCase):
    def test_empty_artifact_set_remains_valid(self) -> None:
        result = adapter_result()
        self.assertEqual(result.artifacts, ())

    def test_canonical_artifact_reference_shape_is_accepted(self) -> None:
        result = adapter_result(artifact())
        self.assertEqual(result.artifacts[0]["artifact_id"], "ART-001")

    def test_optional_media_type_and_sha256_may_be_null(self) -> None:
        result = adapter_result(artifact(media_type=None, sha256=None))
        self.assertIsNone(result.artifacts[0]["media_type"])
        self.assertIsNone(result.artifacts[0]["sha256"])

    def test_artifact_must_be_mapping(self) -> None:
        with self.assertRaisesRegex(ValueError, r"artifact\[0\] must be a mapping"):
            adapter_result(["not", "a", "mapping"])

    def test_required_artifact_fields_must_be_non_empty_strings(self) -> None:
        for field in ("artifact_id", "kind", "uri"):
            with self.subTest(field=field, case="missing"):
                malformed = artifact()
                malformed.pop(field)
                with self.assertRaisesRegex(ValueError, field):
                    adapter_result(malformed)

            with self.subTest(field=field, case="empty"):
                with self.assertRaisesRegex(ValueError, field):
                    adapter_result(artifact(**{field: ""}))

            with self.subTest(field=field, case="wrong_type"):
                with self.assertRaisesRegex(ValueError, field):
                    adapter_result(artifact(**{field: 123}))

    def test_unknown_artifact_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            adapter_result(artifact(vendor_private_field="must-not-leak"))

    def test_optional_scalar_fields_keep_canonical_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "media_type"):
            adapter_result(artifact(media_type=123))
        with self.assertRaisesRegex(ValueError, "sha256"):
            adapter_result(artifact(sha256=123))

    def test_metadata_must_be_object_when_present(self) -> None:
        for malformed in (None, [], "metadata"):
            with self.subTest(metadata=malformed):
                with self.assertRaisesRegex(ValueError, "metadata"):
                    adapter_result(artifact(metadata=malformed))

    def test_artifact_ids_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "artifact_id values must be unique"):
            adapter_result(
                artifact(artifact_id="ART-DUP"),
                artifact(artifact_id="ART-DUP", uri="file:///tmp/second.bin"),
            )

    def test_solidworks_parser_normalizes_artifact_boundary_failure(self) -> None:
        response = {
            "protocol_version": "mrea.solidworks-agent.v1",
            "status": "OK",
            "adapter_name": "SOLIDWORKS_2026",
            "bindings": [],
            "read_back": {"dimensions": [], "constraint_conflicts": []},
            "artifacts": [
                artifact(artifact_id="ART-DUP", kind="SOLIDWORKS_PART"),
                artifact(
                    artifact_id="ART-DUP",
                    kind="SOLIDWORKS_PART",
                    uri="file:///tmp/second.SLDPRT",
                ),
            ],
        }
        with self.assertRaises(CadAdapterError) as captured:
            parse_solidworks_agent_response(response)
        self.assertEqual(
            str(captured.exception),
            "invalid SOLIDWORKS CAD Agent response shape",
        )


if __name__ == "__main__":
    unittest.main()
