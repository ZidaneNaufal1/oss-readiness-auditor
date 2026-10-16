"""Bounded, declarative checks for local repository documentation."""
import argparse
import fnmatch
import html
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path, PurePosixPath

VERSION = "0.1.0"
MAX_FILE = 128 * 1024
MAX_TOTAL = 4 * 1024 * 1024
MAX_CONFIG = 64 * 1024
MAX_ENTRIES = 1000
MAX_MATCHES = 32


class AuditError(ValueError):
    """Static diagnostics never include file content or private absolute paths."""


def rule(identifier, title, paths, tokens=None):
    return {"id": identifier, "title": title, "paths": paths, "contains_any": tokens or []}


DEFAULT_RULES = [
    rule("readme", "Project introduction", ["README.md", "README.rst", "README.txt"]),
    rule("license", "License file", ["LICENSE", "LICENSE.*", "COPYING", "COPYING.*"]),
    rule("run", "Run or installation instructions", ["README.md", "README.rst", "README.txt"], ["quick start", "quickstart", "installation", "getting started", "instalasi", "mulai cepat"]),
    rule("test", "Testing instructions", ["README.md", "README.rst", "CONTRIBUTING.md"], ["pytest", "unittest", "npm test", "dotnet test", "cargo test", "go test"]),
    rule("ci", "CI workflow file", [".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml"]),
    rule("contributing", "Contribution guide", ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"]),
    rule("provenance", "Dependency and source credits", ["THIRD_PARTY.md", "NOTICE", "NOTICE.*", "docs/credits.md"]),
]


def clean_text(value, limit):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit and not any(unicodedata.category(c).startswith("C") or c in "\u2028\u2029" for c in value)


def validate_pattern(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or not re.fullmatch(r"[A-Za-z0-9_./*?-]+", value):
        raise AuditError("invalid_rule_path")
    parts = value.split("/")
    if len(parts) > 6 or any(p in ("", ".", "..") or p.casefold() == ".git" for p in parts):
        raise AuditError("invalid_rule_path")
    if any("*" in p or "?" in p for p in parts[:-1]) or "**" in parts[-1]:
        raise AuditError("invalid_rule_path")
    return value


def validate_rule(value):
    if not isinstance(value, dict) or set(value) - {"id", "title", "paths", "contains_any"} or not {"id", "title", "paths"} <= set(value):
        raise AuditError("invalid_rule")
    if not isinstance(value["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", value["id"]) or not clean_text(value["title"], 120):
        raise AuditError("invalid_rule")
    paths = value["paths"]
    tokens = value.get("contains_any", [])
    if not isinstance(paths, list) or not 1 <= len(paths) <= 8 or not isinstance(tokens, list) or len(tokens) > 16 or any(not clean_text(t, 100) for t in tokens):
        raise AuditError("invalid_rule")
    return rule(value["id"], value["title"], [validate_pattern(p) for p in paths], tokens)


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate_config_key")
        result[key] = value
    return result


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def read_config(path):
    path = Path(path)
    info = path.lstat()
    if linked(info) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CONFIG:
        raise AuditError("unsafe_or_oversized_config")
    with path.open("rb") as stream:
        raw = stream.read(MAX_CONFIG + 1)
    if len(raw) > MAX_CONFIG:
        raise AuditError("unsafe_or_oversized_config")
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=reject_duplicates, parse_constant=lambda _: (_ for _ in ()).throw(AuditError("invalid_config_number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AuditError("invalid_config_json") from exc


def configure(config=None):
    if config is None:
        config = {"version": 1}
    if not isinstance(config, dict) or set(config) - {"version", "rules", "exclude"} or type(config.get("version")) is not int or config["version"] != 1:
        raise AuditError("invalid_config")
    custom = config.get("rules", [])
    if not isinstance(custom, list) or len(custom) > 25:
        raise AuditError("too_many_or_invalid_rules")
    rules = [validate_rule(r) for r in DEFAULT_RULES]
    identifiers = {r["id"] for r in rules}
    for value in custom:
        value = validate_rule(value)
        if value["id"] in identifiers:
            raise AuditError("duplicate_rule_id")
        identifiers.add(value["id"])
        rules.append(value)
    exclude = config.get("exclude", {})
    if not isinstance(exclude, dict) or any(key not in identifiers or not clean_text(reason, 200) for key, reason in exclude.items()):
        raise AuditError("invalid_exclusion")
    return rules, exclude


class Reader:
    def __init__(self, root):
        supplied = Path(root).expanduser()
        info = supplied.lstat()
        if linked(info) or not stat.S_ISDIR(info.st_mode):
            raise AuditError("unsafe_or_invalid_root")
        self.root = supplied.resolve()
        self.cache = {}
        self.directories = {}
        self.total = 0

    def folder(self, parts):
        current = self.root
        for part in parts:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                return None
            if linked(info) or not stat.S_ISDIR(info.st_mode) or not current.resolve().is_relative_to(self.root):
                raise AuditError("unsafe_directory")
        return current

    def matches(self, pattern):
        parts = PurePosixPath(pattern).parts
        folder = self.folder(parts[:-1])
        if folder is None:
            return []
        if folder not in self.directories:
            names = []
            with os.scandir(folder) as entries:
                for entry in entries:
                    names.append(entry.name)
                    if len(names) > MAX_ENTRIES:
                        raise AuditError("directory_entry_limit")
            self.directories[folder] = sorted(names)
        paths = [folder / name for name in self.directories[folder] if fnmatch.fnmatchcase(name, parts[-1])]
        if len(paths) > MAX_MATCHES:
            raise AuditError("matched_file_limit")
        return paths

    def text(self, path):
        if path in self.cache:
            return self.cache[path]
        info = path.lstat()
        if linked(info) or not stat.S_ISREG(info.st_mode) or not path.resolve().is_relative_to(self.root):
            raise AuditError("unsafe_file")
        if info.st_size > MAX_FILE:
            raise AuditError("file_size_limit")
        if self.total + info.st_size > MAX_TOTAL:
            raise AuditError("read_budget_limit")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE + 1)
        self.total += len(raw)
        if len(raw) > MAX_FILE or self.total > MAX_TOTAL:
            raise AuditError("read_budget_limit")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise AuditError("invalid_utf8") from exc
        if "\x00" in text:
            raise AuditError("binary_file")
        self.cache[path] = text
        return text


def check(reader, item):
    matches = set()
    try:
        for pattern in item["paths"]:
            matches.update(reader.matches(pattern))
        if len(matches) > MAX_MATCHES:
            raise AuditError("matched_file_limit")
        eligible = []
        # Inspect every candidate before declaring pass; bad alternatives remain visible.
        for path in sorted(matches):
            content = reader.text(path)
            if content.strip() and (not item["contains_any"] or any(token.casefold() in content.casefold() for token in item["contains_any"])):
                eligible.append(path.relative_to(reader.root).as_posix())
        return {"status": "pass" if eligible else "missing", "reason": "evidence_found" if eligible else "no_matching_evidence", "evidence": eligible}
    except AuditError as exc:
        return {"status": "error", "reason": str(exc), "evidence": []}
    except OSError:
        return {"status": "error", "reason": "unreadable_path", "evidence": []}


def audit(root, config=None):
    rules, exclude = configure(config)
    reader = Reader(root)
    results = []
    for item in rules:
        result = {"id": item["id"], "title": item["title"]}
        if item["id"] in exclude:
            result.update(status="excluded", reason="explicit_exclusion", evidence=[], exclusion_reason=exclude[item["id"]])
        else:
            result.update(check(reader, item))
        results.append(result)
    counts = {name: sum(r["status"] == name for r in results) for name in ("pass", "missing", "excluded", "error")}
    code = 2 if counts["error"] else 1 if counts["missing"] else 0
    return {"tool_version": VERSION, "report_version": 1, "scope": "documentation_signals_only", "exit_code": code, "counts": counts, "results": results}


def md_cell(value):
    # Escape HTML and punctuation, including pipes and link syntax from config or filenames.
    value = "".join(f"&#{ord(c)};" if unicodedata.category(c).startswith("C") or c in "\u2028\u2029" else c for c in value)
    value = html.escape(value, quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def render(report, kind):
    if kind == "json":
        return json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    lines = ["# OSS readiness signals", "", "Documentation signals only; no certification, code execution, or quality score.", "", "| Rule | Status | Reason | Evidence |", "| --- | --- | --- | --- |"]
    for item in report["results"]:
        reason = item.get("exclusion_reason", item["reason"])
        lines.append("| " + " | ".join(md_cell(v) for v in (item["id"], item["status"], reason, ", ".join(item["evidence"]))) + " |")
    counts = report["counts"]
    lines += ["", "Counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()), ""]
    return "\n".join(lines)


def save_report(root, output, content, config_path=None):
    root = Path(root).expanduser().resolve()
    output = Path(output).expanduser()
    resolved = output.resolve()
    if output.is_symlink() or resolved.is_relative_to(root) or (config_path is not None and resolved == Path(config_path).expanduser().resolve()):
        raise AuditError("output_must_be_outside_repository_and_config")
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect local repository documentation without executing its code.")
    parser.add_argument("root", help="Local directory to inspect; Git metadata is not required.")
    parser.add_argument("--config", help="Explicit trusted JSON config; repository configs are never auto-loaded.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", help="New output file outside the inspected directory.")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    try:
        config = read_config(Path(args.config).expanduser()) if args.config else None
        report = audit(args.root, config)
        content = render(report, args.format)
        if args.output:
            save_report(args.root, args.output, content, args.config)
        else:
            print(content, end="")
        return report["exit_code"]
    except AuditError as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
    except (OSError, RuntimeError, UnicodeError):
        print("Audit failed: inaccessible_or_invalid_path", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
