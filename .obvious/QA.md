# QA Guide — icloud-drive-docker

What each quality gate checks, how to reproduce it locally, and what the fixtures prove. Commands verified against base `bb1e027` (see `.obvious/LOCAL-DEV.md` for the verified environment and the Python 3.13 pylint caveat).

## Gates

| Gate | Where it runs | What it checks | Reproduce |
|---|---|---|---|
| PR CI (`ci-pr-test.yml`) | PRs to `main`, path-filtered (`src/**`, `tests/**`, `Dockerfile`, `pylintrc`, `pytest.ini`, `requirements*`, `run-ci.sh` — lines 6-14); manual dispatch possible | `pylint src/ tests/ && pytest` on Python 3.10 (line 63) | `./run-ci.sh` (or the two commands separately) |
| Main CI (`ci-main-test-coverage-deploy.yml`) | Push to `main`, same path filter (6-17) | `pytest` only (61-63) incl. the 100% coverage gate; publishes Allure/coverage reports; builds and pushes `mandarons/icloud-drive:main` (186-225, upstream Docker Hub secrets required) | `pytest` |
| Coverage floor | Every pytest run via `pytest.ini:5` | `--cov-fail-under=100` measured over `src/*` only (`Coveragerc`) — tests are excluded from measurement | `pytest` |
| pylint | PR CI only — never on main pushes | Full `src/` + `tests/` against Google-style `pylintrc` | `pylint src/ tests/` (Python 3.10) |
| pre-commit (local) | Developer machines | ruff, black, isort, flake8, bandit (config `tests/bandit.yaml`), yamllint (config `.yamllint`), prettier, codespell, local pylint via `run-in-env.sh`, `no-commit-to-branch` guard on `main` | `pre-commit run --all-files` |

**Path-filter caveat:** doc-only PRs (README, docs/, .obvious/) trigger **no CI** — the filters only watch source/test/tooling paths. To force the PR workflow, run it via the `workflow_dispatch` trigger on the PR branch (`ci-pr-test.yml:15`).

**Verified baseline (this sandbox, Python 3.13.14):** `pytest` → **179 passed, coverage 100.00%**, exit 0. `pylint src/ tests/` → exit 1 on 3.13 (wrapt 1.12.1 `inspect.formatargspec` ImportError); green on CI's 3.10. Single test: `pytest tests/test_config_parser.py -k get_username --cov-fail-under=0` → 3 passed, exit 0.

## Synthetic fixtures (tests/data/)

All fixtures are synthetic or sample data committed to the repo. The iCloud API surface is mocked with recorded JSON responses — no test opens a network connection to Apple.

| Fixture | Used for |
|---|---|
| `tests/data/__init__.py` | Recorded iCloud API response fixtures (account identifiers, drive listings, session payloads) consumed by `icloudpy.base` mocks |
| `tests/data/photos_data.py` | Recorded Photos API responses (library/album queries, photo versions `original`/`medium`/`thumb`) |
| `test_config.yaml` / `test_config_env.yaml` | Sample configs for `read_config`/`ENV_CONFIG_FILE_PATH` tests; use one-shot `sync_interval: -1` and synthetic `user@test.com` |
| `original.jpeg`, `medium.jpeg`, `thumb.jpeg` | Binary payloads standing in for the three photo versions; also used as a non-archive input in package-handling tests |
| `Project.band.zip`, `ms.band.zip`, `ms.band/`, `Project_original.band/` | GarageBand-style packages exercising zip download, unpack, and `package_exists` mtime+size logic |
| `Fotoksiążka-Wzór.xmcf.zip` | Unicode-filename archive (NFC/NFD normalization paths) |
| `This is a title.md` | Plain file for drive sync assertion (nested Obsidian sample) |

Test runs write scratch output under `tests/temp/` (`tests/__init__.py:14-16`); `run-ci.sh:1-5` cleans generated artifacts.

## iCloud-auth proof boundary

No test, doc, or verification step in this repo requires or permits real iCloud credentials:

- Tests mock `icloudpy` entirely; the account identifiers in fixtures are invented synthetic data (`tests/data/__init__.py`).
- The only credential paths in source — `ENV_ICLOUD_PASSWORD` → keyring (`src/sync.py:66-72`) and SMTP settings (`src/notify.py:27-37`) — are exercised through mocks/monkeypatched keyrings, never with real values.
- CI never holds iCloud credentials; the only secrets referenced in workflows are upstream deployment secrets (Docker Hub, gh-pages deploy key).
- Fixture proofs cannot establish real-world iCloud behavior (rate limits, 2FA flows, actual API responses). Runtime claims about the live service are documented as code-read behavior, e.g. in `docs/persistence-backup-recovery.md`, not as executed proofs.

Keep it that way: never add a real Apple ID, password, session cookie, or SMTP credential to any file in this repo.
