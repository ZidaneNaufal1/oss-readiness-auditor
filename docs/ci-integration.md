# Using the auditor in a consumer CI job

Copy [examples/consumer-ci.yml.txt](../examples/consumer-ci.yml.txt) into a trusted repository as `.github/workflows/oss-audit.yml`. Add a chosen policy file at `.github/oss-audit.json`:

```json
{"version": 1}
```

That activates the seven defaults. Review custom paths and exclusion reasons before extending the config. Configuration is explicitly selected, not automatically discovered. Use synthetic or non-sensitive policy text because rule titles and exclusion reasons appear in reports.

The example installs the v0.3.0 GitHub source archive, then executes the installed command. It needs network access for installation/build tooling, but the audit itself makes no network calls. Runtime dependencies are empty. For immutable source selection, replace the tag URL with an archive URL for a reviewed full commit. This repository has no PyPI release.

The Bash step captures the command's exit status and returns it unchanged: 0 means no missing/error findings among active rules, 1 means missing evidence, 2 means an inspection/configuration/export/argument error. Both 1 and 2 fail the job. All-excluded configs can return 0 with pass=0, so review excluded counts rather than treating green CI as proof of project quality. Do not add `|| true` or ignore every nonzero status.

Reports go into `$RUNNER_TEMP` under a run/attempt-specific filename outside the checkout. The program refuses existing outputs; use a new filename if adding repeated scans to the same job. The template does not publish or upload report artifacts automatically. Add sharing only after reviewing metadata and permissions.

Use ordinary `pull_request` without secret-bearing credentials or privileged target workflows. The audit does not execute inspected code, but checkout, installation, workflow configuration and concurrent filesystem changes have their own trust boundaries. This is a minimal integration example, not an adversarial repository sandbox.

## What this project's CI actually verifies

For each supported OS/Python combination, CI builds a wheel from the checkout, creates a fresh virtual environment, installs that wheel offline without dependencies, and exercises the installed console command and `python -m oss_auditor` outside the source checkout. It compares outputs against direct source execution, tests policy customizations and exit codes, checks import origin/metadata and license presence, and checks exclusive export. These are local consumer-style integration tests. The copyable workflow is supplied for consumers; no external repository adoption is claimed.
