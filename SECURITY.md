# Security

Supported development line: 0.3.x. This is a documentation scanner for trusted, stable local folders, not a sandbox for malicious filesystems or a code security analyzer. Do not run it over sensitive folders merely because a third-party config suggests paths. Read the chosen config and inspect report metadata before sharing. It performs no network requests and never runs target repository code. Package installation/build tooling has a separate trust boundary: install only reviewed source/wheels. No PyPI publication exists for this project; do not assume a similarly named registry package belongs to this maintainer.

For non-sensitive problems, open an issue with a synthetic reproduction. If details require private disclosure, contact the maintainer through an actually available profile contact method first to agree a private channel; do not publish sensitive details. A dedicated private reporting channel and response SLA are not currently promised.
