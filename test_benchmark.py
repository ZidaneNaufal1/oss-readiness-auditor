import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks import run_benchmark as bench


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def spec(self, name):
        return next(s for s in bench.specifications() if s["id"] == name)

    def test_dataset_ids_and_bytes_stable(self):
        first, second = bench.specifications(), bench.specifications()
        self.assertEqual(first, second)
        self.assertEqual(len({s["id"] for s in first}), 10)
        self.assertEqual(len(self.spec("file_at_128k")["files"]["README.md"]), 131072)
        self.assertEqual(len(self.spec("file_over_128k")["files"]["README.md"]), 131073)

    def test_manifest_detects_content_name_and_empty_directory(self):
        root = self.base / "fixture"
        bench.write_fixture(root, self.spec("complete"))
        first = bench.tree_manifest(root)
        (root / "README.md").write_bytes(b"altered")
        self.assertNotEqual(bench.tree_manifest(root), first)
        second = bench.tree_manifest(root)
        (root / "empty").mkdir()
        self.assertNotEqual(bench.tree_manifest(root), second)

    def test_clock_samples_and_preservation(self):
        ticks = iter((10, 30, 50, 90))
        result = bench.run_case(self.base, self.spec("complete"), 2, clock=lambda: next(ticks))
        self.assertEqual(result["timing_ns"], {"samples": [20, 40], "min": 20, "median": 30, "max": 40})
        self.assertTrue(result["source_preserved"])

    def test_incorrect_expectation_fails(self):
        spec = self.spec("complete")
        spec["expected_counts"] = bench.expected_counts(0)
        with self.assertRaisesRegex(ValueError, "unexpected_findings"):
            bench.run_case(self.base, spec, 1)

    def test_nondeterministic_findings_fail(self):
        real = bench.auditor.audit
        reports = [real(self.base), real(self.base)]
        reports[1]["tool_version"] = "changed"
        with patch.object(bench.auditor, "audit", side_effect=reports), self.assertRaisesRegex(ValueError, "nondeterministic"):
            bench.run_case(self.base, self.spec("empty"), 1)

    def test_modified_fixture_fails(self):
        real = bench.auditor.audit
        def modifying(root, config):
            report = real(root, config)
            (root / "unrelated.txt").write_bytes(b"unexpected mutation")
            return report
        with patch.object(bench.auditor, "audit", side_effect=modifying), self.assertRaisesRegex(ValueError, "fixture_modified"):
            bench.run_case(self.base, self.spec("complete"), 1)

    def test_known_false_positive_and_negative_documented(self):
        for name, counts in (("misleading_tokens", bench.expected_counts(7)), ("unrecognized_instructions", bench.expected_counts(5, missing=2))):
            result = bench.run_case(self.base, self.spec(name), 1)
            self.assertEqual(result["actual_counts"], counts)
            self.assertIn("illustration", result["interpretation"])

    def test_limits_and_custom_cases(self):
        names = ("custom_and_exclusion", "file_at_128k", "file_over_128k", "directory_at_1000", "directory_over_1000", "aggregate_read_budget")
        for name in names:
            with self.subTest(name=name):
                result = bench.run_case(self.base, self.spec(name), 1)
                self.assertTrue(result["source_preserved"])
                self.assertEqual(result["actual_counts"], result["expected_counts"])

    def test_repetition_validation(self):
        for value in (0, -1, 51, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bench.run(value)

    def test_corpus_identity_independent_of_timing_and_environment(self):
        with patch.object(bench, "specifications", return_value=[self.spec("empty")]):
            first = bench.run(1)
            second = bench.run(2)
        self.assertEqual(first["dataset_sha256"], second["dataset_sha256"])
        self.assertEqual(first["benchmark_version"], 1)
        self.assertEqual(second["method"]["measured_audits_per_case"], 2)
        self.assertEqual(json.loads(json.dumps(first))["cases"][0]["id"], "empty")


if __name__ == "__main__":
    unittest.main()
