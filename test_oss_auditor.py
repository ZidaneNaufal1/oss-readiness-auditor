import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import oss_auditor as app


class AuditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo # ü"
        self.root.mkdir()

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def complete(self):
        self.put("README.md", "# Example\n## Quick start\npython app.py\n## Tests\npython -m unittest\n")
        self.put("LICENSE", "Synthetic license fixture: not a license grant.")
        self.put("CONTRIBUTING.md", "How to contribute.")
        self.put("THIRD_PARTY.md", "Synthetic credits.")
        self.put(".github/workflows/test.yml", "name: Tests\non: push\n")

    def by_id(self, report, identifier):
        return next(r for r in report["results"] if r["id"] == identifier)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = app.main([str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_complete_repository(self):
        self.complete()
        report = app.audit(self.root)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["counts"], {"pass": 7, "missing": 0, "excluded": 0, "error": 0})

    def test_empty_repository(self):
        report = app.audit(self.root)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["counts"]["missing"], 7)

    def test_readme_alone_does_not_pass_all(self):
        self.put("README.md", "A project")
        report = app.audit(self.root)
        self.assertEqual(self.by_id(report, "readme")["status"], "pass")
        self.assertEqual(self.by_id(report, "run")["status"], "missing")
        self.assertEqual(self.by_id(report, "test")["status"], "missing")

    def test_empty_files_missing(self):
        self.put("LICENSE", " \n")
        self.assertEqual(self.by_id(app.audit(self.root), "license")["status"], "missing")

    def test_casefold_literal_tokens(self):
        self.put("README.md", "QUICK START\nPYTHON -M UNITTEST")
        report = app.audit(self.root)
        self.assertEqual(self.by_id(report, "run")["status"], "pass")
        self.assertEqual(self.by_id(report, "test")["status"], "pass")

    def test_custom_rule_and_exclusion(self):
        self.complete()
        config = {"version": 1, "rules": [{"id": "security", "title": "Security guide", "paths": ["SECURITY.md"], "contains_any": ["report"]}], "exclude": {"ci": "CI lives in an external service"}}
        report = app.audit(self.root, config)
        self.assertEqual(self.by_id(report, "security")["status"], "missing")
        self.assertEqual(self.by_id(report, "ci")["status"], "excluded")
        self.put("SECURITY.md", "Report problems privately")
        self.assertEqual(app.audit(self.root, config)["exit_code"], 0)

    def test_all_excluded_transparent_counts(self):
        report = app.audit(self.root, {"version": 1, "exclude": {r["id"]: "Policy exception" for r in app.DEFAULT_RULES}})
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["counts"]["pass"], 0)
        self.assertEqual(report["counts"]["excluded"], 7)

    def test_unknown_or_empty_exclusion_rejected(self):
        for excluded in ({"unknown": "reason"}, {"ci": ""}, {"ci": "a\nb"}, ["ci"]):
            with self.subTest(excluded=excluded), self.assertRaises(app.AuditError):
                app.configure({"version": 1, "exclude": excluded})

    def test_invalid_config_shapes(self):
        for value in ([], {}, {"version": True}, {"version": 2}, {"version": 1, "unexpected": True}, {"version": 1, "rules": {}}, {"version": 1, "rules": [None]}):
            with self.subTest(value=value), self.assertRaises(app.AuditError):
                app.configure(value)

    def test_invalid_rule_fields(self):
        base = {"id": "custom", "title": "Example", "paths": ["FILE"]}
        for change in ({"id": "Upper"}, {"title": "\x00"}, {"paths": []}, {"contains_any": [""]}, {"command": "echo test"}):
            with self.subTest(change=change), self.assertRaises(app.AuditError):
                app.configure({"version": 1, "rules": [dict(base, **change)]})

    def test_duplicate_rule_ids(self):
        with self.assertRaises(app.AuditError):
            app.configure({"version": 1, "rules": [{"id": "ci", "title": "Override", "paths": ["CI"]}]})

    def test_unsafe_patterns_rejected(self):
        for value in ("../secret", "/etc/passwd", "C:/file", "a\\b", "a//b", ".git/config", "x/.GIT/config", "**/*.md", "docs*/x.md", "a/../file", "a/[x].md"):
            with self.subTest(value=value), self.assertRaises(app.AuditError):
                app.validate_pattern(value)

    def test_rules_limit(self):
        with self.assertRaises(app.AuditError):
            app.configure({"version": 1, "rules": [None] * 26})

    def test_config_duplicate_key_and_nonfinite(self):
        path = self.base / "config.json"
        for content in ('{"version":1,"version":1}', '{"version": NaN}', '{bad', '[]'):
            path.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(app.AuditError):
                app.configure(app.read_config(path))

    def test_explicit_config_utf8_bom(self):
        path = self.base / "config.json"
        path.write_bytes(b'\xef\xbb\xbf{"version":1}')
        self.assertEqual(app.read_config(path), {"version": 1})

    def test_config_size_limit(self):
        path = self.base / "config.json"
        path.write_bytes(b" " * (app.MAX_CONFIG + 1))
        with self.assertRaises(app.AuditError):
            app.read_config(path)

    def test_no_automatic_repository_config(self):
        self.put("auditor.json", '{"command":"touch sentinel"}')
        self.assertEqual(app.audit(self.root)["counts"]["missing"], 7)

    def test_source_contents_not_in_report(self):
        self.put("README.md", "PRIVATE_SAMPLE quick start unittest")
        rendered = app.render(app.audit(self.root), "json")
        self.assertNotIn("PRIVATE_SAMPLE", rendered)
        self.assertNotIn(str(self.root), rendered)
        self.assertIn("README.md", rendered)

    def test_deterministic_output(self):
        self.complete()
        self.assertEqual(app.render(app.audit(self.root), "json"), app.render(app.audit(self.root), "json"))

    def test_read_budget_caches_same_file(self):
        path = self.put("README.md", "quick start unittest")
        reader = app.Reader(self.root)
        reader.text(path)
        reader.text(path)
        self.assertEqual(reader.total, path.stat().st_size)

    def test_file_size_limit_error(self):
        self.put("README.md", "x" * (app.MAX_FILE + 1))
        report = app.audit(self.root)
        self.assertEqual(self.by_id(report, "readme")["reason"], "file_size_limit")
        self.assertEqual(report["exit_code"], 2)

    def test_aggregate_budget_error(self):
        self.complete()
        with patch.object(app, "MAX_TOTAL", 1):
            self.assertEqual(app.audit(self.root)["exit_code"], 2)

    def test_binary_and_invalid_utf8(self):
        for raw, reason in ((b"a\x00", "binary_file"), (b"\xff", "invalid_utf8")):
            self.put("README.md", "").write_bytes(raw)
            self.assertEqual(self.by_id(app.audit(self.root), "readme")["reason"], reason)

    def test_directory_and_match_limits(self):
        self.put("LICENSE.a", "fixture")
        self.put("LICENSE.b", "fixture")
        with patch.object(app, "MAX_MATCHES", 1):
            self.assertEqual(self.by_id(app.audit(self.root), "license")["reason"], "matched_file_limit")
        with patch.object(app, "MAX_ENTRIES", 1):
            self.assertEqual(app.audit(self.root)["exit_code"], 2)

    def test_directory_instead_of_file_errors(self):
        (self.root / "README.md").mkdir()
        self.assertEqual(self.by_id(app.audit(self.root), "readme")["reason"], "unsafe_file")

    def test_link_guard_portable(self):
        self.put("README.md", "fixture")
        real = app.linked
        with patch.object(app, "linked", side_effect=lambda info: real(info) or app.stat.S_ISREG(info.st_mode)):
            self.assertEqual(self.by_id(app.audit(self.root), "readme")["reason"], "unsafe_file")
        with patch.object(app, "linked", return_value=True), self.assertRaises(app.AuditError):
            app.Reader(self.root)

    def test_bad_alternative_does_not_hide_error(self):
        self.put("README.md", "good")
        self.put("README.txt", "\x00")
        self.assertEqual(self.by_id(app.audit(self.root), "readme")["status"], "error")

    def test_windows_reparse_flag_rejected(self):
        info = SimpleNamespace(st_mode=app.stat.S_IFDIR, st_file_attributes=0x400)
        self.assertTrue(app.linked(info))

    def test_unsafe_subfolder_rejected(self):
        (self.root / "docs").mkdir()
        reader = app.Reader(self.root)
        with patch.object(app, "linked", return_value=True), self.assertRaises(app.AuditError):
            reader.folder(["docs"])

    def test_no_commands_executed_and_files_unchanged(self):
        self.complete()
        sentinel = self.root / "sentinel"
        self.put("README.md", f"Quick start\npython -c 'open({str(sentinel)!r}, \"w\")'\nunittest")
        self.put(".github/workflows/test.yml", f"run: touch {sentinel}")
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        app.audit(self.root)
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(sentinel.exists())

    def test_markdown_escapes_injected_formatting(self):
        for value in ("[x](https://invalid.example)", "a|b", "<script>", "a\nb"):
            escaped = app.md_cell(value)
            self.assertNotIn("<script>", escaped)
            self.assertNotIn("\n", escaped)
        self.assertIn("\\|", app.md_cell("a|b"))

    def test_exclusive_output_and_source_guard(self):
        self.complete()
        report = app.render(app.audit(self.root), "json")
        output = self.base / "report.json"
        app.save_report(self.root, output, report)
        with self.assertRaises(FileExistsError):
            app.save_report(self.root, output, "overwrite")
        self.assertEqual(output.read_text(encoding="utf-8"), report)
        with self.assertRaises(app.AuditError):
            app.save_report(self.root, self.root / "new.json", report)
        config = self.base / "config.json"
        with self.assertRaises(app.AuditError):
            app.save_report(self.root, config, report, config)

    def test_cli_pass_missing_error(self):
        self.assertEqual(self.cli("--format", "json")[0], 1)
        self.complete()
        code, output, errors = self.cli("--format", "json")
        self.assertEqual((code, errors), (0, ""))
        self.assertEqual(json.loads(output)["counts"]["pass"], 7)
        self.put("README.md", "\x00")
        self.assertEqual(self.cli()[0], 2)

    def test_cli_config_operational_error(self):
        code, output, error = self.cli("--config", str(self.base / "missing.json"))
        self.assertEqual((code, output), (2, ""))
        self.assertNotIn(str(self.base), error)
        self.assertNotIn("Traceback", error)


if __name__ == "__main__":
    unittest.main()
