# Sources and dependencies

Runtime uses Python standard library only. No external implementation code, artwork or datasets are copied into the project. Test/demo repositories are generated from synthetic strings; their placeholder license text does not grant a real license and their workflows are never executed by the auditor.

Development/build tooling: setuptools 80.9.0 (MIT) and wheel 0.45.1 (MIT), fetched from PyPI into the development environment. They are not runtime dependencies or vendored into the tool's wheel. pip/venv from the Python environment perform local installation tests. Their licenses remain with the upstream projects. The package wheel includes the project's MIT license and ownership metadata.

GitHub CI uses actions/checkout@v4 and actions/setup-python@v5 under their respective upstream licenses. These are development infrastructure, not runtime dependencies or code relicensed by this project's MIT license. Python itself retains its original license.

Ciel / OpenAI Codex assisted implementation, testing and documentation. Ownership/maintenance is credited to Muhammad Zidane Naufal Azzam. No official company endorsement or certification is implied.
