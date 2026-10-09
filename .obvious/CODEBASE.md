# Codebase Map — icloud-drive-docker

Fork of [mandarons/icloud-drive-docker](https://github.com/mandarons/icloud-drive-docker): a Python client that periodically **downloads** iCloud Drive files and Photos to a local directory. It never uploads (`README.md:16`). The iCloud protocol work is delegated to the `icloudpy` library (pinned `icloudpy==0.5.0`, `requirements.txt:4`, which hard-pins `requests==2.28.1`). All line references below are to the tree at base `2061137d421d2059abee8ea348d86f8aa4b5de42`.

## Entry flow

`src/main.py:6-7` → `sync.sync()` (`src/sync.py:48-154`) → an infinite loop that, on every cycle: re-reads `config.yaml` from `ENV_CONFIG_FILE_PATH` or the repo-root default (`src/sync.py:56-61`, default built at `src/__init__.py:21-23`); pings the telemetry heartbeat (`src/sync.py:62` → `src/usage.py:121-131`); resolves the password from `ENV_ICLOUD_PASSWORD` (stored into the OS keyring) or the keyring (`src/sync.py:66-72`); builds an `ICloudPyService` client — with `.com.cn` endpoints when `app.region: china` (`src/sync.py:24-45`, region parsed at `src/config_parser.py:366-383`); aborts the cycle into a retry loop if interactive 2FA is required (`src/sync.py:77, 96-106`); otherwise runs drive sync (`src/sync.py:78-84`) and photo sync (`src/sync.py:85-91`); then computes the next sleep from the two `sync_interval` values (`src/sync.py:120-154`). A negative `sync_interval` makes the loop exit after one pass — the one-shot mode the test config uses (`src/sync.py:146-153`, `tests/data/test_config.yaml` with `sync_interval: -1`).

## src/ modules

| Module | Purpose | Key functions |
|---|---|---|
| `src/main.py` | Container entrypoint (7 lines). | `sync.sync()` at `src/main.py:6-7`. |
| `src/__init__.py` | Defaults, config reading, logging. Destination/interval/env constants at `src/__init__.py:11-24` (`session_data` cookie dir default at line 24). `read_config` at 29-42; logger setup — `icloud.log` file handler plus colored console — at 106-138. | `read_config`, `get_logger`, `ColorfulConsoleFormatter` |
| `src/config_parser.py` | Getters over the YAML config using path traversal (`traverse_config_path` 21-27). Destinations: `prepare_root_destination` (`app.root`, default `./icloud`, mkdirs) 109-123; `prepare_drive_destination` 207-223; `prepare_photos_destination` 242-258. Interval defaults: retry 600 s (54-66), drive/photos sync 1800 s (69-96). `remove_obsolete` defaults to **false** for both (226-240, 261-277). Photo filters incl. valid file sizes `original/medium/thumb` (279-364). SMTP getters (126-204). `folder_format` (386-393). `region` global/china (366-383). | `get_username`, `prepare_*_destination`, `get_*` |
| `src/sync.py` | Orchestration loop (see Entry flow). | `sync`, `get_api_instance` |
| `src/sync_drive.py` | Recursive iCloud Drive mirror. Filtering: `wanted_file` (extension regex, 20-34), `wanted_folder`/`wanted_parent_folder` (37-75), gitwildmatch `ignore` via pathspec (24-27, 39-41). Change detection is **mtime + size**, not checksums: `file_exists` (124-146), `package_exists` (93-121; `rmtree` of a changed package at 118). Package handling: `is_package` detects `/packageDownload?` URLs (181-186); `process_package` unpacks zip/gzip via libmagic (149-178). `download_file` streams 4 MiB chunks and stamps the local mtime with the remote mtime (189-206). `remove_obsolete` deletes local files/dirs absent from the remote listing (230-245), only when `drive.remove_obsolete: true` and only at the top level (`sync_directory` 312-313). Per-item exceptions inside `sync_directory` are deliberately swallowed to keep the loop alive (`sync_drive.py:288-290, 309-311`). Entry: `sync_drive` (317-333). | `sync_drive`, `sync_directory`, `download_file`, `process_package` |
| `src/sync_photos.py` | iCloud Photos mirror. Filenames embed identity + version: `name__size__base64(photo.id).ext`, with in-place renames migrating older layouts (`generate_file_name` 25-62); optional `folder_format` date subfolders (43-52). `photo_exists` compares **size only** (65-77). `download_photo` stamps mtime with the photo's `added_date` (80-94). Albums recurse into subalbums (118-141); `all_albums: true` mirrors album structure, `false` collapses into `all/` (159-200); `remove_obsolete` deletes unseen files (144-156, applied at 202-203). | `sync_photos`, `sync_album`, `process_photo` |
| `src/notify.py` | Email alert when 2FA has expired. Throttled to one email per 24 h (9-23); SMTP with optional STARTTLS and auth (27-37); message tells the user to `docker exec` and re-authenticate with `--session-directory=/app/session_data` (52-60). | `send`, `build_message` |
| `src/email_message.py` | Minimal plaintext MIME message builder (7-51). | `EmailMessage` |
| `src/usage.py` | Telemetry to endpoints baked in at Docker build time (`NEW_INSTALLATION_ENDPOINT`/`NEW_HEARTBEAT_ENDPOINT`, 11-12; unset in dev). Keeps a tiny JSON cache named `.data` in the sync root (10, 18-40); posts install/heartbeat pings carrying app name/version and installation id (43-96); all network failures are swallowed (50-51, 88-89). `alive()` runs every cycle (121-131). | `alive`, `heartbeat`, `install` |

## Configuration surface

`config.yaml` (repo root) is the sample config consumed by `read_config` (`src/__init__.py:21-23`). Path layout: `app.root` (default `./icloud`) > `drive.destination` / `photos.destination` (`src/config_parser.py:109-123, 207-223, 243-259`). The file is re-read **every sync cycle** (`src/sync.py:56-61`), so edits apply without restart. `tests/data/test_config.yaml` and `tests/data/test_config_env.yaml` are the test variants (one-shot intervals, fixture filters).

## Tests map

`pytest.ini:3-5` targets `tests/` with a hard `--cov-fail-under=100` gate over `src/*` (`Coveragerc`). Helper module `tests/__init__.py:11-16` defines `DATA_DIR`/`TEMP_DIR`/`DRIVE_DIR`/`PHOTOS_DIR` paths; `update_config` (19-23) rewrites the test config; `mocked_usage_post` (26-41) stubs telemetry HTTP.

| Test file | Covers | Notes |
|---|---|---|
| `tests/test_config_parser.py` | Every getter in `src/config_parser.py` | 465 lines |
| `tests/test_src_init.py` | `src/__init__.py` config reading + logger | |
| `tests/test_sync.py` | Orchestration loop, password/keyring paths, 2SA retry | |
| `tests/test_sync_drive.py` | Drive filtering, change detection, packages, obsolete removal | 1299 lines |
| `tests/test_sync_photos.py` | Photo naming, existence checks, albums, obsolete removal | |
| `tests/test_notify.py` / `tests/test_usage.py` | Email throttle/build; telemetry cache & heartbeat | |

Fixtures live in `tests/data/` (inventory in `.obvious/QA.md`). The `icloudpy` API is mocked with recorded responses (`tests/data/__init__.py`, `tests/data/photos_data.py`) — no test contacts Apple.

## CI workflows

| Workflow | Trigger | What runs |
|---|---|---|
| `.github/workflows/ci-pr-test.yml` | PRs to `main`, **path-filtered** to `src/**`, `tests/**`, `Dockerfile`, `pylintrc`, `pytest.ini`, `requirements*`, `run-ci.sh` (lines 6-14); manual `workflow_dispatch` (15) | `pylint src/ tests/ && pytest` on Python 3.13 (line 63) |
| `.github/workflows/ci-main-test-coverage-deploy.yml` | Push to `main`, same path filter (9-17) | `pytest` only (63), publishes Allure/coverage to gh-pages, builds/pushes `mandarons/icloud-drive:main` to Docker Hub (205-215) |
| `.github/workflows/close-stale.yml` | Daily cron | Stales issues after 365 days |
| `.github/workflows/official-release-to-docker-hub.yml` | `v*.*.*` tags (8-10) | Builds/pushes `mandarons/icloud-drive:<ver>` + `:latest` (29, 33) |

Consequences worth knowing: **doc-only PRs do not trigger CI** (path filters), and pylint runs only on PRs, never on main pushes. No workflow runs existed in this fork at wave start; the Docker Hub and gh-pages destinations belong to upstream and require upstream secrets.

## GUI status: stubbed, inactive

`gui/` is a Nuxt 3 scaffold (bun lockfile; `pages/index.vue` is a 3-line placeholder) committed as an explicit "Stubbing out GUI" snapshot (`bb1e027`). Nothing in the runtime references it: the container command is `python -u ./src/main.py` (`Dockerfile:28`) and no CI workflow touches `gui/`. Treat it as an experimental stub, not a feature.

## Tooling

`run-ci.sh` = cleanup + `pylint src/ tests/` + `pytest` + `allure generate` (the last needs the Allure CLI binary, preinstalled only in `.devcontainer/Dockerfile`). `.pre-commit-config.yaml` runs ruff, black, isort, flake8, bandit (config `tests/bandit.yaml`), yamllint, prettier, codespell, a local pylint hook via `run-in-env.sh`, and `no-commit-to-branch` guarding `main`.
