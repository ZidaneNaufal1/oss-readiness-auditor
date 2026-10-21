# Initial case study: making repository gaps visible

## Problem and audience

A new contributor often cannot find how to run tests, install a project, identify its license or trace its dependencies. Beginner maintainers need a repeatable first pass before asking someone else to try their repository.

## Scope delivered

The CLI checks seven finite sets of documentation signals, adds user-defined file/token rules, and writes JSON or Markdown. Results distinguish missing evidence, operational errors and explicit exceptions. It does not award a score or infer legal, code or community quality.

## Decisions and tradeoffs

Declarative JSON avoids running repository-provided plugins. Explicit config loading keeps a target repo from choosing its own policy automatically. Bounded shallow folder listing makes scan scope predictable, at the cost of rejecting large folders and unsupported layouts. Literal substring matching is easy to explain but can mistake examples/comments for instructions; results therefore require human review. Every matching candidate is inspected before a rule passes so a broken alternative is not silently ignored. Reports show relative filenames and static diagnostics without copying file content.

## Evidence

`python -m unittest -v` covers complete/missing fixtures, configuration errors, custom rules, exclusions, encoding/binary failures, path and size limits, stable reports and output preservation. `python examples/run_demo.py` demonstrates 0 pass/7 missing becoming 7 pass/0 missing after adding synthetic documents; it checks target bytes stay unchanged. These are controlled demonstrations, not user adoption or proof that placeholder licenses/workflows are valid. CI repeats tests, demo and self-audit from clean checkouts across supported OS/Python versions.

## Current limits and next work

Version 0.2.0 adds a wheel, console entry point and consumer CI template. Ten integration checks install into a fresh virtual environment and run from outside the source checkout: import origin and distribution metadata prove the installed code is exercised, while source/installed report comparison covers JSON/Markdown, custom rules, exceptions and failure codes. Runtime dependencies remain empty, and the report/config version stays at 1. CI builds and repeats these checks on supported Windows/Linux Python versions.

Version 0.3.0 adds [a documented ten-case synthetic benchmark](../benchmarks/README.md). A measured seven-repetition sample on a constrained Windows/CPython 3.14 host recorded a 7.664 ms median for the five-file complete case; timing includes only warm in-process audit calls, not setup or CLI startup. This is an observed sample, not a cross-machine guarantee or proof of improvement.

The study intentionally exposes two semantic errors: negated installation/unittest text still passes literal checks, while launch/tox guidance is missed. At 1001 root entries, every default rule errors, including CI because its GitLab alternative also lists root. Expected outcomes, deterministic reports, unchanged sources and boundary reasons are checked on each benchmark run. The first draft incorrectly expected CI to pass that over-limit case; the failing test prompted inspection of all candidate paths and correction of the documented expectation, not a change to scanner behavior.

Actual external feedback and representative real-world performance measurements are still pending. Next is an internal trial across maintainer-owned projects. The maintainer's ability to explain and improve the implementation is a separate learning milestone.

Owner/maintainer: Muhammad Zidane Naufal Azzam. Implementation, tests and documentation assisted by Ciel / OpenAI Codex, with limitations and provenance disclosed.
