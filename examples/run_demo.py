"""Synthetic fixtures; no network or repository code execution."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "oss_auditor.py"


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder) / "fixture"
        root.mkdir()
        def run(*args, expected):
            result = subprocess.run([sys.executable, str(CLI), str(root), "--format", "json", *args], capture_output=True, text=True)
            assert result.returncode == expected, result.stderr
            return json.loads(result.stdout) if result.stdout else None
        empty = run(expected=1)
        assert empty["counts"]["missing"] == 7
        fixtures = {"README.md": "# Example\nQuick start\npython example.py\nTests: python -m unittest", "LICENSE": "Synthetic license fixture, not a grant", "CONTRIBUTING.md": "Synthetic contribution guide", "THIRD_PARTY.md": "Synthetic credits", ".github/workflows/tests.yml": "name: Fixture\non: push"}
        for name, content in fixtures.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        before = {name: (root / name).read_bytes() for name in fixtures}
        complete = run(expected=0)
        assert complete["counts"]["pass"] == 7
        output = Path(folder) / "report.json"
        run("--output", str(output), expected=0)
        run("--output", str(output), expected=2)
        run("--output", str(root / "report.json"), expected=2)
        assert before == {name: (root / name).read_bytes() for name in fixtures}
        print(json.dumps({"empty": empty["counts"], "complete": complete["counts"]}, indent=2))
        print("Demo passed: missing/pass signals, source preservation, exclusive external export.")


if __name__ == "__main__":
    main()
