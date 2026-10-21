# Synthetic benchmark, dataset v1

This corpus measures **warm, in-process `audit(root, config)` calls**, and checks known documentation-signal behavior. It is not a representative collection of public projects, an accuracy score, a cold disk benchmark, a security test or a CLI/installation benchmark.

## Reproduce

From this source checkout with Python 3.10+:

```console
python benchmarks/run_benchmark.py --repetitions 7 --output ../benchmark-new.json
```

Choose a new output outside the checkout; existing files are refused. Omit `--output` to print JSON. Repetitions must be 1–50; default 7. The runner generates only its own synthetic temporary files, never loads target code, and removes its temporary directory afterwards. It creates roughly two thousand tiny files plus a 4 MiB limit fixture, so restrictive/slow filesystems can dominate setup time. Set TEMP/TMP to a writable folder when necessary.

The code generates fixed bytes and configs, then records each case's file/directory counts, byte total, content/path/config SHA256 fingerprints, expected/actual counts and rule findings. The dataset fingerprint covers those fixture identities and expected counts. Timings and environment are deliberately outside that identity. Dataset v1 SHA256:

```text
bc678e0fbd2c1079430cd2de28a17d0fd9d84a5df05b24e35aa9d82e90726b50
```

Before timing each case, one untimed audit checks expectations. Seven measured audits follow in the same process, each with a fresh Reader but warm OS caches. Each measured report must equal the warmup report exactly. Tree manifests before and after the case must match (relative file names, bytes, and directory names). Failed expectations, non-deterministic results or changed sources abort the runner with exit 2. These assertions are correctness gates; there are **no timing thresholds**.

`perf_counter_ns` covers directory listing, file reads, rule checks and report object creation. Fixture creation, manifest hashing, JSON/Markdown serialization, CLI startup, installation and cleanup are outside the measured interval. The JSON retains every sample and min/median/max, Python/tool versions, OS/release/architecture, clock resolution, warmup and repetition counts. CPU model, RAM, disk model, power state and background load are not controlled/recorded; this limits cross-machine comparisons. A portable workload can be reproduced; identical elapsed times are not promised.

## Cases and observed behavior

| Case | Files / bytes | Expected signal outcome | Interpretation |
| --- | --- | --- | --- |
| empty | 0 / 0 | 7 missing, exit 1 | No docs present |
| complete | 5 / 214 | 7 pass, exit 0 | Synthetic text signals only |
| misleading_tokens | 5 / 213 | 7 pass, exit 0 | Negation containing installation/unittest still matches: false-positive illustration |
| unrecognized_instructions | 5 / 214 | 5 pass, 2 missing, exit 1 | Launch/tox instructions lack recognized literals: false-negative illustration |
| custom_and_exclusion | 6 / 255 | 7 pass, 1 excluded, exit 0 | Extra SECURITY rule and visible CI exception |
| file_at_128k | 5 / 131209 | 7 pass, exit 0 | README exactly 131072 bytes accepted |
| file_over_128k | 5 / 131210 | 4 pass, 3 error, exit 2 | One byte over README limit errors readme/run/test |
| directory_at_1000 | 1000 / 23099 | 7 pass, exit 0 | Root has 1000 entries, including .github folder |
| directory_over_1000 | 1001 / 23122 | 7 error, exit 2 | All defaults list root; CI also checks root .gitlab-ci.yml alternative |
| aggregate_read_budget | 36 / 4194470 | 6 pass, 1 error, exit 2 | 32 license candidates plus README exceed 4 MiB read budget |

False-positive/negative labels refer to the intentionally stated fixture meaning, not a measured statistical error rate. No working application, real license validity or runnable CI exists in these synthetic fixtures. A green complete case therefore must not be described as a production-ready project.

## Recorded sample — 2026-10-21

[Full JSON evidence](results/windows-python314.json) was produced on Windows 11 AMD64, CPython 3.14.0, tool 0.3.0, seven measured repetitions per case plus one warmup. The host is a constrained local workspace; no performance improvement over earlier versions is claimed.

| Case | Median ms | Min–max ms |
| --- | ---: | ---: |
| empty | 1.326 | 0.779–2.088 |
| complete | 7.664 | 5.973–10.694 |
| misleading_tokens | 8.905 | 5.891–10.336 |
| unrecognized_instructions | 8.783 | 5.829–9.545 |
| custom_and_exclusion | 5.987 | 4.632–7.880 |
| file_at_128k | 9.056 | 5.466–12.313 |
| file_over_128k | 9.566 | 8.073–12.207 |
| directory_at_1000 | 17.573 | 14.966–20.450 |
| directory_over_1000 | 19.547 | 17.007–30.201 |
| aggregate_read_budget | 36.851 | 30.363–39.614 |

The same findings and unchanged-source checks also run in CI on Ubuntu/Windows with Python 3.10/3.12/3.14, using three measured repetitions to keep validation bounded. CI timings are observational and may differ. See the release's CI links for those logs. Do not average unrelated fixture cases into a universal speed or accuracy claim.
