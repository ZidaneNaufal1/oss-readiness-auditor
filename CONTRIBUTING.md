# Contributing

Use Python 3.10+; no runtime dependencies to install. Run `python -m unittest -v`, `python examples/run_demo.py`, and `python oss_auditor.py . --config examples/config.json --format json`. CI covers Ubuntu/Windows on Python 3.10/3.12/3.14.

For packaging changes, use a development venv, install `requirements-dev.txt`, build with `python -m pip wheel . --no-build-isolation --no-deps --wheel-dir dist`, then run `python scripts/verify_install.py dist/oss_readiness_auditor-0.3.0-py3-none-any.whl`. This verifies the actual installed distribution from outside the source checkout. Keep version metadata, release documentation and workflow wheel paths aligned when bumping the tool version.

For rule or benchmark changes, run `python benchmarks/run_benchmark.py --repetitions 3` and review expected findings rather than changing them just to make tests pass. Update dataset version/fingerprints and explanations intentionally if fixture content or expectations change. Timing variations are not test failures; incorrect findings, nondeterminism and source mutation are.

Report bugs with OS/Python/tool version, a small synthetic fixture, chosen config, expected and actual finding. Remove private paths, document contents and sensitive policy reasons. Discuss rule changes with a concrete false positive/negative example. Keep declarative rules free of executable hooks. A change needs behavior tests, documentation of false-positive limits, and changelog notes; do not silently alter report-version or config semantics.

Submit a focused PR stating the problem, resulting behavior and validation. Maintainer review determines acceptance. AI assistance is welcome when disclosed and verified. Be respectful; give evidence-based feedback and allow maintainers time to respond. No contributor is expected to share private repositories or secrets.
