"""Repeatable synthetic corpus checks and warm in-process audit timings."""
import argparse
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import oss_auditor as auditor

DATASET_VERSION = 1
BASE = {
    "README.md": b"# Synthetic example\nQuick start: python example.py\nTests: python -m unittest\n",
    "LICENSE": b"Synthetic license fixture, not a license grant.\n",
    "CONTRIBUTING.md": b"Synthetic contribution guide.\n",
    "THIRD_PARTY.md": b"Synthetic source credits.\n",
    ".github/workflows/tests.yml": b"name: Synthetic fixture\non: push\n",
}


def expected_counts(passed, missing=0, excluded=0, errors=0):
    return {"pass": passed, "missing": missing, "excluded": excluded, "error": errors}


def specifications():
    """Constants intentionally do not follow changed runtime limits silently."""
    full = dict(BASE)
    misleading = dict(BASE, **{"README.md": b"Installation is not supported. Do not run unittest; no working tests exist.\n"})
    unfamiliar = dict(BASE, **{"README.md": b"# Launch\nUse the interpreter on example.py.\n# Verification\nUse tox -e check.\n"})
    custom = dict(BASE, **{"SECURITY.md": b"Contact the maintainer to report issues.\n"})
    config = {"version": 1, "rules": [{"id": "security", "title": "Security guide", "paths": ["SECURITY.md"], "contains_any": ["report"]}], "exclude": {"ci": "Synthetic external-CI exception"}}
    at_size = dict(BASE, **{"README.md": BASE["README.md"].ljust(131072, b" ")})
    over_size = dict(BASE, **{"README.md": BASE["README.md"].ljust(131073, b" ")})
    at_entries = dict(BASE)
    at_entries.update({f"filler-{i:04d}.txt": b"Synthetic ignored file\n" for i in range(995)})
    over_entries = dict(at_entries, **{"filler-over.txt": b"Synthetic ignored file\n"})
    budget = dict(BASE)
    del budget["LICENSE"]
    budget.update({f"LICENSE.{i:02d}": b"Synthetic license fixture\n".ljust(131072, b" ") for i in range(32)})
    cases = [
        ("empty", {}, None, expected_counts(0, missing=7), 1, {}, "Seven absent documentation signals."),
        ("complete", full, None, expected_counts(7), 0, {}, "Seven nonempty file/text signals; placeholder license/workflow validity is not tested."),
        ("misleading_tokens", misleading, None, expected_counts(7), 0, {}, "False-positive illustration: run/test pass despite explicit negation and no working instructions."),
        ("unrecognized_instructions", unfamiliar, None, expected_counts(5, missing=2), 1, {}, "False-negative illustration: launch/tox guidance exists but does not match default literals."),
        ("custom_and_exclusion", custom, config, expected_counts(7, excluded=1), 0, {}, "Custom SECURITY rule passes; ci excluded visibly with reason."),
        ("file_at_128k", at_size, None, expected_counts(7), 0, {}, "README exactly 131072 bytes is accepted."),
        ("file_over_128k", over_size, None, expected_counts(4, errors=3), 2, {"readme": "file_size_limit", "run": "file_size_limit", "test": "file_size_limit"}, "README one byte over limit errors all three dependent checks."),
        ("directory_at_1000", at_entries, None, expected_counts(7), 0, {}, "Root has exactly 1000 entries, including .github directory."),
        ("directory_over_1000", over_entries, None, expected_counts(0, errors=7), 2, {"readme": "directory_entry_limit", "ci": "directory_entry_limit"}, "Root has 1001 entries; every default rule errors, including CI because its .gitlab-ci.yml alternative lists the root."),
        ("aggregate_read_budget", budget, None, expected_counts(6, errors=1), 2, {"license": "read_budget_limit"}, "32 matching license files of 128 KiB exceed total 4 MiB once README bytes are included."),
    ]
    return [{"id": name, "files": files, "config": config, "expected_counts": counts, "expected_exit": code, "expected_reasons": reasons, "interpretation": note} for name, files, config, counts, code, reasons, note in cases]


def tree_manifest(root):
    files = []
    directories = []
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        elif path.is_file():
            raw = path.read_bytes()
            files.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        else:
            raise ValueError("unexpected_fixture_entry")
    canonical = json.dumps({"files": files, "directories": directories}, sort_keys=True, separators=(",", ":")).encode()
    return {"file_count": len(files), "directory_count": len(directories), "total_bytes": sum(f["bytes"] for f in files), "sha256": hashlib.sha256(canonical).hexdigest()}


def write_fixture(root, spec):
    root.mkdir()
    for name, raw in spec["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def assert_findings(report, spec):
    if report["counts"] != spec["expected_counts"] or report["exit_code"] != spec["expected_exit"]:
        raise ValueError("unexpected_findings:" + spec["id"])
    findings = {r["id"]: r for r in report["results"]}
    if any(findings[name]["reason"] != reason for name, reason in spec["expected_reasons"].items()):
        raise ValueError("unexpected_diagnostic:" + spec["id"])


def run_case(parent, spec, repetitions, clock=time.perf_counter_ns):
    root = parent / spec["id"]
    write_fixture(root, spec)
    before = tree_manifest(root)
    warmup = auditor.audit(root, spec["config"])
    assert_findings(warmup, spec)
    samples = []
    for _ in range(repetitions):
        start = clock()
        report = auditor.audit(root, spec["config"])
        end = clock()
        if end < start:
            raise ValueError("non_monotonic_clock")
        assert_findings(report, spec)
        if report != warmup:
            raise ValueError("nondeterministic_findings:" + spec["id"])
        samples.append(end - start)
    if tree_manifest(root) != before:
        raise ValueError("fixture_modified:" + spec["id"])
    policy_digest = hashlib.sha256(json.dumps(spec["config"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"id": spec["id"], "fixture": before, "config_sha256": policy_digest, "expected_counts": spec["expected_counts"], "actual_counts": warmup["counts"], "exit_code": warmup["exit_code"], "findings": [{"id": r["id"], "status": r["status"], "reason": r["reason"]} for r in warmup["results"]], "interpretation": spec["interpretation"], "source_preserved": True, "deterministic_findings": True, "timing_ns": {"samples": samples, "min": min(samples), "median": statistics.median(samples), "max": max(samples)}}


def run(repetitions=7):
    if type(repetitions) is not int or not 1 <= repetitions <= 50:
        raise ValueError("repetitions_must_be_1_to_50")
    specs = specifications()
    with tempfile.TemporaryDirectory(prefix="oss-benchmark-") as folder:
        cases = [run_case(Path(folder), spec, repetitions) for spec in specs]
    identity = [{"id": case["id"], "fixture": case["fixture"], "config_sha256": case["config_sha256"], "expected_counts": case["expected_counts"]} for case in cases]
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    clock = time.get_clock_info("perf_counter")
    return {"benchmark_version": 1, "dataset_version": DATASET_VERSION, "tool_version": auditor.VERSION, "report_version": 1, "dataset_sha256": digest, "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(), "os": platform.system(), "os_release": platform.release(), "machine": platform.machine()}, "method": {"timer": "perf_counter_ns", "clock_resolution_seconds": clock.resolution, "warmup_audits_per_case": 1, "measured_audits_per_case": repetitions, "scope": "audit(root, config) in one process; fresh Reader each audit; warm OS caches; includes directory listing, reads and checks", "excluded": "fixture creation, manifest hashing, JSON/Markdown serialization, CLI startup, installation and cleanup", "thresholds": "none; timings are observational, not universal performance or accuracy claims"}, "cases": cases}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--output", help="New JSON file outside this source checkout.")
    args = parser.parse_args(argv)
    try:
        result = run(args.repetitions)
        content = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
        if args.output:
            auditor.save_report(PROJECT, args.output, content)
        else:
            print(content, end="")
        return 0
    except (ValueError, OSError):
        print("Benchmark failed: check repetitions, fixture findings, filesystem access or output location.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
