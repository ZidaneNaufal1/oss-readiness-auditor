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

Version 0.1.0 runs from a source checkout. Packaging and a consumer CI example are next. Actual user feedback and representative performance measurements are still pending. The maintainer's ability to explain and improve the implementation is a separate learning milestone.

Owner/maintainer: Muhammad Zidane Naufal Azzam. Implementation, tests and documentation assisted by Ciel / OpenAI Codex, with limitations and provenance disclosed.
