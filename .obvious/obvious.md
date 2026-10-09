# Obvious orientation — icloud-drive-docker

This repository is a fork of `mandarons/icloud-drive-docker`: a Dockerized Python daemon
that periodically downloads iCloud Drive content and Photos into local volumes according
to `config.yaml` (entry flow `src/main.py` → `src/sync.py` scheduler → `src/sync_drive.py`
/ `src/sync_photos.py`). End users run the published container against their own iCloud
account, so everything the app touches at runtime is personal data. The Nuxt app under
`gui/` is a deliberately stubbed-out experiment, not a working feature.

## Highest-priority constraints for automated work

1. **No real credentials, accounts, or network in tests — ever.** Never commit iCloud
   credentials, session data, or personal data; never point tests or verification at a
   real iCloud account or live network. Use the synthetic fixtures under `tests/data/`
   and mock the `icloudpy` service layer. There is no runtime password in the repo: the
   container reads it from `ENV_ICLOUD_PASSWORD` or prompts, and the sample `config.yaml`
   is a template with placeholder values only.
2. **Dependency pins are load-bearing.** `requirements.txt` hard-pins
   `icloudpy==0.5.0`, which transitively pins `requests==2.28.1` (plus older
   keyring/tzlocal/certifi). Upgrading requests requires an icloudpy upgrade whose
   changed session API also needs test-mock updates — do not bump these casually; see
   the comment block in `requirements.txt`.
3. **The coverage floor is 100%.** `pytest.ini` sets `--cov-fail-under=100` over
   `src/`; CI runs `pylint src/ tests/ && pytest` on the pinned toolchain from
   `requirements-test.txt`. Any new code path needs tests that reach it.
4. **Tests establish behavior, not implementation.** Assert observable outcomes
   (files written, filters applied, notifications sent), not internal call patterns.
   See `.obvious/QA.md` for the gate commands and fixture inventory.
5. **Never publish or deploy from this fork.** The Docker Hub release workflow
   (`.github/workflows/official-release-to-docker-hub.yml`) belongs to the upstream
   namespace (`mandarons/icloud-drive`); do not trigger, retarget, or "fix" it to run
   here, and do not publish releases.
6. **Sync intervals and removal flags are data-destructive levers.**
   `remove_obsolete: true` deletes local files that fall outside the current sync set
   (`src/sync_drive.py:230-245`); treat related test fixtures as synthetic-only and
   document any behavior change rather than tuning defaults.
