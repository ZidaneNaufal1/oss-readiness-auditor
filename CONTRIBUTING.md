# Contributing

Use Python 3.10+; no runtime dependencies to install. Run `python -m unittest -v`, `python examples/run_demo.py`, and `python oss_auditor.py . --config examples/config.json --format json`. CI covers Ubuntu/Windows on Python 3.10/3.12/3.14.

Report bugs with OS/Python/tool version, a small synthetic fixture, chosen config, expected and actual finding. Remove private paths, document contents and sensitive policy reasons. Discuss rule changes with a concrete false positive/negative example. Keep declarative rules free of executable hooks. A change needs behavior tests, documentation of false-positive limits, and changelog notes; do not silently alter report-version or config semantics.

Submit a focused PR stating the problem, resulting behavior and validation. Maintainer review determines acceptance. AI assistance is welcome when disclosed and verified. Be respectful; give evidence-based feedback and allow maintainers time to respond. No contributor is expected to share private repositories or secrets.
