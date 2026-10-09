# Local Development — icloud-drive-docker

Reproducible dev setup verified against base `bb1e027` on this sandbox (Python 3.13.14, no Docker). CI targets Python 3.10 (`Dockerfile:1`, both test workflows). Every command below was executed successfully in this sandbox unless marked otherwise.

## Setup

```bash
git clone https://github.com/dbhagen/icloud-drive-docker && cd icloud-drive-docker
python3 -m venv venv && . venv/bin/activate
pip install -U pip
pip install -r requirements-test.txt   # includes -r requirements.txt
```

`requirements-test.txt` pins pytest 6.2.5, pytest-cov 2.11.1, pylint 2.9.3, coverage 5.4, allure-pytest, pre-commit. Installation is clean on Python 3.13 (verified in this sandbox).

## Running the checks

**Lint + tests (the CI script):**

```bash
./run-ci.sh
```

`run-ci.sh` deletes generated artifacts first (`icloud/`, `session_data/`, `icloud.log`, `.pytest_cache`, `htmlcov` — lines 1-5), then runs `pylint src/ tests/` and `pytest` (lines 7, 9), then `allure generate` (line 11). The Allure step needs the **Allure CLI binary**, which pip does not provide (allure-pytest only writes `allure-results/`); it is preinstalled in the devcontainer (`.devcontainer/Dockerfile`). Without it, run the two real gates directly.

**Tests only (verified on Python 3.13.14):**

```bash
pytest          # 179 passed, coverage 100.00% — meets --cov-fail-under=100 (pytest.ini:5)
```

**Lint on this sandbox (known failure, documented workaround):**

`pylint src/ tests/` **fails on Python 3.13** with the pinned requirements: pylint 2.9.3 pulls wrapt 1.12.1, which imports `inspect.formatargspec`, removed in Python 3.13 (verified: `ImportError` at `wrapt/decorators.py:34`, pylint exit 1). It passes on CI's Python 3.10. Options until tooling is refreshed (owned by the dependency unit, not docs):

- Run lint under Python 3.10 (devcontainer or any 3.10 interpreter), or
- Treat the pylint half of `run-ci.sh` as CI-provided and run `pytest` locally.

**Single test (verified):**

```bash
pytest tests/test_config_parser.py -k get_username --cov-fail-under=0
```

The `--cov-fail-under=0` override is required: `pytest.ini:5` applies the 100% gate to *every* pytest invocation, so a partial run otherwise exits 1 with `Required test coverage of 100% not reached` even when the selected tests pass (verified).

## Local vs CI differences

| | CI | This sandbox |
|---|---|---|
| Python | 3.10 (`Dockerfile:1`, workflows) | 3.13.14 |
| pylint | green | broken (wrapt/formatargspec, see above) |
| pytest + 100% coverage | green | green — 179 passed, 100.00% |
| Docker | builds multi-arch images | unavailable |
| Allure CLI | via devcontainer/actions | not installed; `allure-results/` still produced |

## Runtime environment variables

Set at container/runtime level, not needed for tests (they run against `tests/data/test_config.yaml`):

- `ENV_CONFIG_FILE_PATH` — absolute path overriding the default `config.yaml` lookup (`src/__init__.py:18, 21-23`; consumed at `src/sync.py:57-60`).
- `ENV_ICLOUD_PASSWORD` — iCloud app-specific password; stored into the OS keyring each cycle (`src/sync.py:66-70`). Never put real credentials in the repo or test fixtures.

## No Docker locally

The sandbox cannot build or run the image (`Dockerfile`, `Dockerfile-debug`). Container-path claims in docs derive from reading `Dockerfile` (`WORKDIR /app` line 13, `COPY . /app/` line 22, `CMD ["python", "-u", "./src/main.py"]` line 23), not from a local container run. Telemetry endpoints (`NEW_INSTALLATION_ENDPOINT`, `NEW_HEARTBEAT_ENDPOINT`) are Docker **build args** (`Dockerfile:11-12, 19-20`); unset locally, which makes `src/usage.py` skip network posts (fail-silent, `src/usage.py:50-51, 88-89`).

## Optional tooling

- `pre-commit install` — hooks in `.pre-commit-config.yaml` (ruff, black, isort, flake8, bandit, yamllint, prettier, codespell, local pylint via `run-in-env.sh`, `no-commit-to-branch` for `main`).
- The devcontainer (`.devcontainer/devcontainer.json`) ships Python 3.10 + Allure 2.20.1 and is the closest match to CI.
