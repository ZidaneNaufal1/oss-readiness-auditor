# Changelog

## 0.3.0 — 2026-10-21

- Reproducible ten-case synthetic corpus and warm in-process audit timing runner.
- Expected findings, SHA256 fixture identities, raw timing samples and environment/method metadata.
- Repetition determinism and source-preservation gates; tests for incorrect expectations and mutation.
- Explicit false-positive/negative illustrations and exact file/directory/read-budget boundaries.
- Recorded Windows/CPython 3.14 sample with seven repetitions and stated limitations; CI repeats three times without timing thresholds.
- Scanner behavior and report/config version 1 preserved; tool_version updates to 0.3.0.

## 0.2.0 — 2026-10-20

- Installable wheel with `oss-readiness-auditor` entry point and `python -m oss_auditor` support.
- Standard pyproject metadata, MIT license files and no runtime dependencies.
- Pinned development build tools and ten isolated wheel installation checks.
- Installed/source equivalence for reports, custom rules, exclusions and exit codes 0/1/2.
- Consumer CI template and integration guide; six-platform/version matrix now builds and verifies the package.
- Report/config version 1 and scanner behavior preserved; tool_version updates to 0.2.0.
- No PyPI publication, external adoption or user feedback claimed.

## 0.1.0 — 2026-10-16

- Seven built-in documentation signal rules and declarative custom checks.
- Strict versioned JSON configuration; exclusions with visible reasons.
- Bounded local file reads, link/reparse checks, no target code execution.
- Deterministic JSON/Markdown reports with explicit pass/missing/excluded/error states.
- Exclusive report export outside the inspected directory.
- Behavior tests, isolated demo, self-audit and cross-platform CI.
- English documentation with Indonesian summary; case study, contribution guide and staged roadmap.

This initial CLI release is a foundation for the continuing flagship project. Installable distribution and real feedback remain planned.
