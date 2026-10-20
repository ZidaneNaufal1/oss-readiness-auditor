"""Verify a built wheel in a fresh venv, outside the source checkout."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "oss_auditor.py"
WHEEL = None


class InstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name).resolve()
        cls.env = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME"):
            cls.env.pop(key, None)
        cls.env["PYTHONUTF8"] = "1"
        cls.venv = cls.base / "installed"
        venv.EnvBuilder(with_pip=True).create(cls.venv)
        bin_dir = cls.venv / ("Scripts" if os.name == "nt" else "bin")
        cls.python = bin_dir / ("python.exe" if os.name == "nt" else "python")
        cls.command = bin_dir / ("oss-readiness-auditor.exe" if os.name == "nt" else "oss-readiness-auditor")
        subprocess.run([str(cls.python), "-I", "-m", "pip", "--isolated", "install", "--no-cache-dir", "--no-index", "--no-deps", str(WHEEL)], cwd=cls.base, env=cls.env, check=True)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)
        self.root = self.work / "repo # unicode ü"
        self.root.mkdir()
        fixtures = {"README.md": "Quick start\npython app.py\npython -m unittest", "LICENSE": "Synthetic fixture, not a license grant", "THIRD_PARTY.md": "Synthetic source credits", "CONTRIBUTING.md": "Contribute", ".github/workflows/test.yml": "name: Synthetic fixture", "SECURITY.md": "Contact to report problems"}
        for name, text in fixtures.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def compare(self, *args, expected=0, root=None):
        root = root or self.root
        results = []
        commands = ([sys.executable, "-I", str(SOURCE)], [str(self.command)], [str(self.python), "-I", "-m", "oss_auditor"])
        for command in commands:
            result = subprocess.run([*command, str(root), *args], cwd=self.work, env=self.env, text=True, encoding="utf-8", capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            results.append((result.stdout, result.stderr))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        return results[0][0]

    def test_import_and_metadata_from_installed_environment(self):
        code = "import importlib.metadata as m, json, oss_auditor; print(json.dumps({'path':oss_auditor.__file__, 'version':oss_auditor.VERSION, 'metadata':m.version('oss-readiness-auditor'), 'requires':m.requires('oss-readiness-auditor')}))"
        result = subprocess.run([str(self.python), "-I", "-c", code], cwd=self.work, env=self.env, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertTrue(Path(data["path"]).resolve().is_relative_to(self.venv))
        self.assertEqual(data["version"], data["metadata"])
        self.assertFalse(data["requires"])
        version = subprocess.run([str(self.command), "--version"], cwd=self.work, env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(version.stdout.strip(), data["version"])

    def test_json_report_equivalence(self):
        output = json.loads(self.compare("--format", "json"))
        self.assertEqual(output["report_version"], 1)
        self.assertEqual(output["counts"]["pass"], 7)

    def test_markdown_report_equivalence(self):
        self.assertIn("Counts: pass=7", self.compare("--format", "markdown"))

    def test_custom_rule_equivalence(self):
        config = self.work / "custom.json"
        config.write_text(json.dumps({"version": 1, "rules": [{"id": "security", "title": "Security guide", "paths": ["SECURITY.md"], "contains_any": ["report"]}]}), encoding="utf-8")
        report = json.loads(self.compare("--config", str(config), "--format", "json"))
        self.assertEqual(report["counts"]["pass"], 8)

    def test_exclusion_equivalence(self):
        config = self.work / "exclude.json"
        config.write_text(json.dumps({"version": 1, "exclude": {"ci": "Checked separately"}}), encoding="utf-8")
        report = json.loads(self.compare("--config", str(config), "--format", "json"))
        self.assertEqual(report["counts"]["excluded"], 1)
        self.assertEqual(report["counts"]["pass"], 6)

    def test_missing_exit_one(self):
        empty = self.work / "empty"
        empty.mkdir()
        report = json.loads(self.compare("--format", "json", expected=1, root=empty))
        self.assertEqual(report["counts"]["missing"], 7)

    def test_inspection_error_exit_two(self):
        (self.root / "README.md").write_bytes(b"\x00")
        report = json.loads(self.compare("--format", "json", expected=2))
        self.assertGreater(report["counts"]["error"], 0)

    def test_invalid_config_exit_two(self):
        config = self.work / "bad.json"
        config.write_text('{"version":2}', encoding="utf-8")
        self.assertEqual(self.compare("--config", str(config), expected=2), "")

    def test_installed_export_preserves_sources_and_refuses_overwrite(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        output = self.work / "report.json"
        args = [str(self.command), str(self.root), "--format", "json", "--output", str(output)]
        subprocess.run(args, cwd=self.work, env=self.env, check=True)
        report = output.read_bytes()
        retry = subprocess.run(args, cwd=self.work, env=self.env, capture_output=True)
        self.assertEqual(retry.returncode, 2)
        self.assertEqual(output.read_bytes(), report)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_wheel_contains_module_entrypoint_and_license(self):
        with zipfile.ZipFile(WHEEL) as archive:
            names = archive.namelist()
        self.assertIn("oss_auditor.py", names)
        self.assertTrue(any(name.endswith("/entry_points.txt") for name in names))
        self.assertTrue(any(name.endswith("/LICENSE") for name in names))
        self.assertFalse(any(name.startswith(("test_", "scripts/")) for name in names))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    WHEEL = args.wheel.resolve(strict=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstalledTests))
    sys.exit(0 if result.wasSuccessful() else 1)
