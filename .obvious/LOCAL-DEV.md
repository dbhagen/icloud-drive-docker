# Local Development — icloud-drive-docker

Reproducible dev setup verified against base `2061137d` on this sandbox (Python 3.13.14, no Docker). CI also targets Python 3.13 (`python-version: "3.13"` in both test workflows; container base `python:3.13-alpine`), so local and CI toolchains now match. Every command below was executed successfully in this sandbox unless marked otherwise.

## Setup

```bash
git clone https://github.com/dbhagen/icloud-drive-docker && cd icloud-drive-docker
python3 -m venv venv && . venv/bin/activate
pip install -U pip
pip install -r requirements-test.txt   # includes -r requirements.txt
```

`requirements-test.txt` (as of PR #2) pins pytest 8.4.2, pytest-cov 6.3.0, pylint 3.3.9, coverage 7.16.2, allure-pytest 2.16.2, plus pre-commit. `requirements.txt` hard-pins `icloudpy==0.5.0` → transitively `requests==2.28.1` (rationale in the comment block at `requirements.txt:1-4`). Installation is clean on Python 3.13 (verified in this sandbox, exit 0).

## Running the checks

**Lint + tests (the CI script):**

```bash
./run-ci.sh
```

`run-ci.sh` deletes generated artifacts first (`icloud/`, `session_data/`, `icloud.log`, `.pytest_cache`, `htmlcov` — lines 1-5), then runs `pylint src/ tests/` and `pytest` (lines 7, 9), then `allure generate` (line 11). The Allure step needs the **Allure CLI binary**, which pip does not provide (allure-pytest only writes `allure-results/`); it is preinstalled in the devcontainer (`.devcontainer/Dockerfile:12-16`). Without it, run the two real gates directly.

**Tests (verified on Python 3.13.14):**

```bash
pytest          # 193 passed, coverage 100.00% — meets --cov-fail-under=100 (pytest.ini:5)
```

**Lint (verified green on Python 3.13.14):**

```bash
pylint src/ tests/   # exit 0, rated 10.00/10 with pylint 3.3.9
```

The historical 3.13 blocker (pylint 2.9.3 pulling wrapt 1.12.1, which imported the removed `inspect.formatargspec`) is resolved by the pylint 3.3.9 pin from the dependency-update PR; wrapt is no longer in the dependency tree.

**Single test (verified):**

```bash
pytest tests/test_config_parser.py -k get_username --cov-fail-under=0
```

The `--cov-fail-under=0` override is required: `pytest.ini:5` applies the 100% gate to *every* pytest invocation, so a partial run otherwise exits 1 with `Required test coverage of 100% not reached` even when the selected tests pass (verified: 3 passed, exit 0).

## Local vs CI differences

| | CI | This sandbox |
|---|---|---|
| Python | 3.13 (workflows) / 3.13-alpine (container) | 3.13.14 — matches |
| pylint | green | green — 10.00/10, exit 0 |
| pytest + 100% coverage | green | green — 193 passed, 100.00% |
| Docker | builds multi-arch images (multi-stage `Dockerfile`) | unavailable |
| Allure CLI | via devcontainer/actions | not installed; `allure-results/` still produced |

## Runtime environment variables

Set at container/runtime level, not needed for tests (they run against `tests/data/test_config.yaml`):

- `ENV_CONFIG_FILE_PATH` — absolute path overriding the default `config.yaml` lookup (`src/__init__.py:18, 21-23`; consumed at `src/sync.py:57-60`).
- `ENV_ICLOUD_PASSWORD` — iCloud app-specific password; stored into the OS keyring each cycle (`src/sync.py:66-70`). Never put real credentials in the repo or test fixtures.

## No Docker locally

The sandbox cannot build or run the image (`Dockerfile`, `Dockerfile-debug`). Container-path claims in docs derive from reading the multi-stage `Dockerfile` (build stage `FROM python:3.13-alpine` line 1; telemetry build args `NEW_INSTALLATION_ENDPOINT`/`NEW_HEARTBEAT_ENDPOINT` lines 11-12; runtime stage `WORKDIR /app` line 17, `COPY . /app/` line 26, `CMD ["python", "-u", "./src/main.py"]` line 28), not from a local container run. Build args unset locally make `src/usage.py` skip network posts (fail-silent, `src/usage.py:50-51, 88-89`).

## Optional tooling

- `pre-commit install` — hooks in `.pre-commit-config.yaml` (ruff, black, isort, flake8, bandit, yamllint, prettier, codespell, local pylint via `run-in-env.sh`, `no-commit-to-branch` for `main`).
- The devcontainer (`.devcontainer/devcontainer.json`) now ships a Python 3.13 image (`.devcontainer/Dockerfile:1`) + Allure 2.20.1 and is the closest match to CI.
