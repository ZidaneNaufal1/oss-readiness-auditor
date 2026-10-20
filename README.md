# oss-readiness-auditor

[![Tests](https://github.com/ZidaneNaufal1/oss-readiness-auditor/actions/workflows/tests.yml/badge.svg)](https://github.com/ZidaneNaufal1/oss-readiness-auditor/actions/workflows/tests.yml)

Inspect a local repository for documentation signals that help a new contributor get started. Find missing license files, run/test instructions, contribution notes, CI files and source credits. Use declarative custom rules and explicit exceptions to fit a project's needs; export JSON for automation or Markdown for a review.

**v0.2.0 adds installable packaging and CI integration to the initial CLI.** Findings are file/text signals, not a quality score, security review, legal opinion, certification, or eligibility assessment for any company's program. A file can exist yet be incorrect; a literal token can occur in an unrelated example. Review the evidence yourself.

## Quick start

Python **3.10+**, standard library only at runtime. Run directly from source or install the reviewed release in a virtual environment. No account, API key or network access is needed when auditing. Git metadata is not required.

```console
git clone https://github.com/ZidaneNaufal1/oss-readiness-auditor.git
cd oss-readiness-auditor
python oss_auditor.py .
python oss_auditor.py . --config examples/config.json --format json
python oss_auditor.py . --format markdown --output ../audit-report.md
```

### Installation

From the trusted source checkout:

```console
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on Linux/macOS. Then:

```console
python -m pip install .
oss-readiness-auditor --version
oss-readiness-auditor . --config examples/config.json --format json
python -m oss_auditor . --format markdown
```

Alternatively install the release directly with `python -m pip install "https://github.com/ZidaneNaufal1/oss-readiness-auditor/archive/refs/tags/v0.2.0.tar.gz"`. This project has **not** been published to PyPI; a similarly named registry project should not be assumed to be this tool. Initial installation may download setuptools/wheel build tools. The installed package declares no runtime dependencies. Tag references can be moved; pin a reviewed full commit archive when strict source immutability is required. Only install source whose build code is trusted; the auditor's no-execution guarantee applies to inspected targets, not Python package installation.

`oss-readiness-auditor`, `python -m oss_auditor`, and `python oss_auditor.py` share the same implementation. A matching release produces identical reports and exit codes; report version 1 and config version 1 remain unchanged. `tool_version` is now 0.2.0.

### CI consumer example

See [the workflow template](examples/consumer-ci.yml.txt) and [integration guide](docs/ci-integration.md). The `.txt` suffix keeps this example inactive until copied into a consumer repository. The supplied workflow explicitly loads `.github/oss-audit.json`, writes a new report outside the checkout, and preserves exit codes 1 and 2 as job failures. Audit trust boundaries still apply to folders and policy being checked.

Replace `.` with a trusted local project directory to inspect another project. Output goes to stdout unless `--output` is supplied. Export requires a **new file outside the inspected directory**, in an existing parent directory. A report may still contain private filenames, custom rule titles and exclusion reasons; review it before sharing.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | No missing/error findings among active rules; explicit exclusions may exist |
| 1 | At least one missing finding, no inspection errors |
| 2 | Inspection error, invalid config/arguments, or export failure |

Rule-level errors still produce a report; configuration/root/export failures produce a static diagnostic on stderr without a report. Error takes precedence over missing. All-excluded rules return 0 with **pass=0**, making the policy exception visible. Counts are not percentages or quality scores.

## Built-in checks

All matching files must be regular, readable UTF-8 (optional BOM), nonempty after whitespace stripping, and within the limits below. A matching binary, linked or unreadable alternative makes its rule error even if another alternative would pass.

| ID | Candidate paths | Additional signal |
| --- | --- | --- |
| readme | README.md, README.rst, README.txt | Nonempty text |
| license | LICENSE, LICENSE.*, COPYING, COPYING.* | Nonempty text; no license identification |
| run | README.md, README.rst, README.txt | Literal quick start, quickstart, installation, getting started, instalasi, or mulai cepat |
| test | README.md, README.rst, CONTRIBUTING.md | Literal pytest, unittest, npm test, dotnet test, cargo test, or go test |
| ci | .github/workflows/*.yml, *.yaml in that same folder; .gitlab-ci.yml | Nonempty text; YAML is not parsed or executed |
| contributing | CONTRIBUTING.md, .github/CONTRIBUTING.md | Nonempty text |
| provenance | THIRD_PARTY.md, NOTICE, NOTICE.*, docs/credits.md | Nonempty text |

Text matching is case-insensitive literal substring matching. It does not understand Markdown headings, code fences, negation, comments, language semantics or whether commands work. Filename matching is case-sensitive (`README.md` differs from `readme.md`); directory lookup follows the operating system. Evidence paths are sorted and relative to the inspected root. Raw file contents, matched lines, token values, absolute root paths and timestamps are not included in reports. Rule/config metadata is included as documented.

## Custom rules and exceptions

Only an **explicit** `--config` is loaded. A config found inside an inspected repo is never loaded automatically. Treat a chosen config as trusted policy: it can affect which files are read and which checks are excluded.

```json
{
  "version": 1,
  "exclude": {"ci": "CI runs in an external service; verify separately"},
  "rules": [
    {
      "id": "security",
      "title": "Security reporting guide",
      "paths": ["SECURITY.md", ".github/SECURITY.md"],
      "contains_any": ["report", "contact"]
    }
  ]
}
```

Custom rules **append** to the seven defaults. IDs are unique lowercase identifiers (`[a-z][a-z0-9_-]{0,39}`); default IDs cannot be overridden. `paths` means alternatives, and `contains_any` means any literal token in a single nonempty candidate file. An omitted/empty token list requires only nonempty text. This format is project-specific JSON, not JSON Schema and not executable Python plugins.

- Root keys: `version` (integer 1, required), `rules` (optional list), `exclude` (optional object). Unknown fields and duplicate JSON keys are rejected.
- At most 25 custom rules (32 total), eight patterns per rule, 16 tokens per rule. Titles 1–120 characters, tokens 1–100, exclusion reasons 1–200; all must contain non-whitespace text and no control/format/line separator characters. Surrounding whitespace is retained in metadata/tokens.
- An exclusion must name a known rule and contain a reason. It appears as `excluded`, with no candidate files inspected for that rule.
- Patterns are relative ASCII paths, at most 200 characters and six components. `/` separates folders. Only letters, digits, `_`, `.`, `/`, `*`, `?`, `-` are supported. Wildcards only in the filename; `**`, bracket globs, absolute paths, empty components, `.`/`..`, backslashes and `.git` components are rejected.
- Unknown rule types, commands, hooks, regexes, imports and network endpoints are not supported.

## Example report

For an empty fixture, the Markdown report includes:

```text
| readme | missing | no_matching_evidence |  |
| license | missing | no_matching_evidence |  |
...
Counts: pass=0, missing=7, excluded=0, error=0
```

JSON has `tool_version`, `report_version` (1), `scope` (`documentation_signals_only`), `exit_code`, `counts`, and `results`. Each result includes `id`, `title`, `status`, a static `reason`, and relative `evidence` paths; exclusions also include `exclusion_reason`. The same unchanged input/config yields the same report. Markdown escapes HTML, formatting punctuation and control characters rather than rendering names as links.

## Read and write boundaries

This program reads local files only. It does not import target modules, run Git/hooks/installers/tests/workflows, evaluate commands, fetch URLs, or fix target files. Export outside the root keeps the inspected tree unchanged. Use ordinary trusted directories, not a live or adversarial filesystem: path checks are not a sandbox or a consistent filesystem snapshot. Parent aliases/hardlinks and concurrent file replacement are not isolated. Final root, candidate file and traversed subfolder symlinks/reparse points are refused. Explicit config final symlinks/reparse points are refused; its parent directories remain trusted.

Limits per audit: config 64 KiB; candidate file 128 KiB; total read budget 4 MiB (successfully decoded files are cached); 1000 directory entries per inspected folder; 32 matched files per pattern/rule. Exceeding a limit is an error, never a silent pass/truncation. The scanner lists only folders named by rules, without a recursive tree walk. A large root directory may exceed its entry limit even if most entries are unrelated. Read caching avoids repeatedly reading the same README across checks. Budget checks assume stable files; concurrent growth is outside the snapshot guarantee.

Exports use exclusive creation and never overwrite an existing file or the config. They are not atomic: a process/disk failure may leave a partial newly created report. Parent directories are not auto-created. Do not publish reports or policy reasons containing secrets.

## Tests and demo

```console
python -m unittest -v
python examples/run_demo.py
python oss_auditor.py . --config examples/config.json --format json
```

To build and verify the installed distribution, use a development virtual environment:

```console
python -m pip install -r requirements-dev.txt
python -m pip wheel . --no-build-isolation --no-deps --wheel-dir dist
python scripts/verify_install.py dist/oss_readiness_auditor-0.2.0-py3-none-any.whl
```

The verifier creates a fresh venv, installs only that wheel using `--no-index --no-deps`, then runs outside the checkout with source lookup environment variables removed. Ten installation checks cover package origin/metadata/license/entry point, JSON/Markdown equivalence, custom rules, exclusions, exit codes 0/1/2 and source-preserving export. Building requires the pinned development tools; installing a prebuilt wheel requires no network or runtime dependencies. Wheel generation can leave local `build/`, `dist/` and `*.egg-info/` artifacts, which Git ignores.

The isolated synthetic demo checks an empty and complete fixture, verifies source bytes remain unchanged, and verifies existing/internal output paths are rejected. Tests cover rule matching, configs, exclusions, limits, bad files, path checks, report escaping, deterministic output and CLI exit codes. Fake license/workflow strings in tests prove signal detection, not legal or workflow validity. CI runs all checks on Ubuntu/Windows × Python 3.10/3.12/3.14 from clean checkouts. In restrictive sandboxes, set `TEMP`/`TMP` to a writable working folder for tests/demo.

## Roadmap and maintenance

The core, installable wheel and consumer CI template are available; the flagship project remains under development. Next: measure a documented synthetic dataset, review false positives/negatives and improve rule explanations. Actual voluntary feedback will be recorded only after trials happen. No external users, feedback, accepted contributions or performance targets are claimed yet. See [ROADMAP](ROADMAP.md) and [case study](docs/case-study.md).

Owner/maintainer: **Muhammad Zidane Naufal Azzam** ([ZidaneNaufal1](https://github.com/ZidaneNaufal1)). Implementation, tests and documentation were developed with disclosed **Ciel / OpenAI Codex** assistance. [MIT](LICENSE); [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), [THIRD_PARTY](THIRD_PARTY.md), [CHANGELOG](CHANGELOG.md).

## Ringkasan Bahasa Indonesia

Alat lokal Python untuk menemukan kekurangan dokumen repository: README, lisensi, cara menjalankan/tes, CI, panduan kontribusi dan kredit sumber. Ada aturan JSON tambahan, pengecualian beralasan, laporan JSON/Markdown, serta batas pembacaan. Isi repo tidak dijalankan dan ekspor wajib ke file baru di luar repo. Hasilnya sinyal keberadaan teks/file, bukan penilaian kualitas, sertifikasi atau jaminan kelayakan program. Versi 0.2.0 sudah dapat diinstal dengan command `oss-readiness-auditor`, disertai tes instalasi terisolasi dan contoh integrasi CI. Benchmark dan feedback nyata masih tahap lanjutan.
