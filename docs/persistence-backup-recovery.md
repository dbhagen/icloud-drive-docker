# Persistence, Backup & Recovery

Grounded in the actual code at base `bb1e027d93a750803f43a1a104fccb594bdd6db7`. Every behavioral claim carries a `file:line` citation into this repository. Runtime claims about Apple's live service are code-read behavior, not executed proofs (see `.obvious/QA.md`, "iCloud-auth proof boundary").

This client is a **one-way downloader** (`README.md:16`); everything it persists is written to local disk.

## Where the container writes

With the standard run recipe (`README.md:23`) and the default config, inside the container:

| Path | What it holds | Written by | Must be backed up? |
|---|---|---|---|
| `/app/config.yaml` | Runtime configuration (mounted in) | User | Yes — it is user intent |
| `/app/session_data` | iCloud session state: session JSON + LWP cookie file | icloudpy, via `cookie_directory` (`src/sync.py:27, 43`; default constant `src/__init__.py:24`) | **Yes** — avoids re-doing 2FA |
| `/app/icloud` (`app.root`, sample value `config.yaml:13`) | Sync root; created with `makedirs` (`src/config_parser.py:109-123`) | Sync | Yes — the downloaded data |
| `/app/icloud/drive` (`drive.destination`, sample `config.yaml:29`) | Mirrored iCloud Drive tree | `sync_drive` (`src/sync_drive.py:317-333`) | Yes |
| `/app/icloud/photos` (`photos.destination`, sample `config.yaml:45`) | Mirrored iCloud Photos | `sync_photos` (`src/sync_photos.py:159-203`) | Yes |
| `/app/icloud/.data` | Telemetry cache: installation id + last heartbeat timestamp (JSON) | `src/usage.py:10, 18-40, 121-131` | No — recreates itself; losing it only re-registers the installation id |
| `/app/icloud.log` | Log file, written to the process CWD (`Dockerfile:13` sets `/app`) | Logger (`src/__init__.py:20, 118`) | No — diagnostics only |

The `notify.py` 2FA email also tells users the session lives in `/app/session_data` (`src/notify.py:58-60`), matching the README mounts (`README.md:23, 43`).

### Keyring, not config: where the password lives

The password is never stored in `config.yaml`. Each cycle, `ENV_ICLOUD_PASSWORD` (if set) is written into the OS keyring under the username (`src/sync.py:66-70`); otherwise the keyring is read (`src/sync.py:72`). The keyring backend comes from icloudpy's pins (`keyring==23.11.0` + `keyrings.alt==4.2.0`, verified from the `icloudpy-0.5.0` wheel metadata) — the `keyrings.alt` file backend persists inside the container filesystem, **not** in any mounted volume. A replaced container therefore loses the keyring copy; that is benign as long as `ENV_ICLOUD_PASSWORD` is still provided, which re-seeds it on the next cycle (`src/sync.py:66-70`).

## What the sync actually writes (and how identity is preserved)

- **Drive files** are streamed in 4 MiB chunks to `<destination>/<path>` and then stamped with the *remote* mtime via `os.utime` (`src/sync_drive.py:195-202`).
- **Drive packages** (GarageBand-style bundles, detected by the `/packageDownload?` URL, `src/sync_drive.py:181-186`) are downloaded as a single zip/gzip and unpacked in place via libmagic type detection (`src/sync_drive.py:149-178`).
- **Photos** are written as `name__size__base64(photo.id).ext` — the remote photo id and version size are embedded in the filename, which is how the sync recognizes previously downloaded versions; older layouts are migrated by rename (`src/sync_photos.py:25-62`). Local mtime is stamped with the photo's `added_date` (`src/sync_photos.py:89-90`). Optional `folder_format` adds date subfolders (`src/sync_photos.py:43-52`).

## What state is kept — and what is not

**There is no local state database.** The code keeps no SQLite/JSON index of what has been synced. Change detection re-derives everything on each cycle from:

1. The filesystem itself: drive change detection compares local vs remote **mtime + size** (`src/sync_drive.py:124-146`; same for packages at 93-121 — a changed package is deleted with `rmtree` and re-downloaded, line 118). Photo change detection compares **size only** (`src/sync_photos.py:65-77`).
2. Photo identity embedded in filenames (the base64 photo-id suffix, `src/sync_photos.py:36-41`).
3. The icloudpy session (cookies + session JSON under `session_data/`).
4. The keyring password (see above).
5. The `.data` telemetry cache (not user state).

Consequences: deleting any of these does not corrupt anything — it only changes how much is re-downloaded. Conversely, because local mtimes equal remote mtimes after a successful download (`src/sync_drive.py:201-202`, `src/sync_photos.py:89-90`), **a restore that does not preserve mtimes will re-download everything** on the next cycle (harmless, potentially slow).

## What to back up

1. `config.yaml` (your copy with real values — keep it out of git; the repo-root one is a sample).
2. `session_data/` — restores the authenticated session.
3. The sync root (e.g. `icloud/`) — drive + photos trees, **with mtimes preserved**.

Optional: `.data` and `icloud.log` — telemetry cache and diagnostics; not required for recovery.

## Restore procedure

1. Recreate the container with the same mounts as the original run (`README.md:23` or the compose file, `README.md:28-44`), with `ENV_ICLOUD_PASSWORD` set.
2. Restore `config.yaml` to its mounted path.
3. Restore `session_data/` to `/app/session_data`.
4. Restore the sync root preserving timestamps — e.g. `tar -xpzf backup.tar.gz -C /data/icloud` or `rsync -a src/ /data/icloud/` (both preserve mtimes by default). If mtimes were lost, expect a full re-download on the first cycle; the data is still correct.
5. Start the container and watch the log: `Drive synced` / `Photos synced` (`src/sync.py:81, 88`) or a 2FA notice (`src/sync.py:97`).
6. If the restored session was expired, interactive re-authentication is needed: the command from the notification email (`src/notify.py:60`) or `README.md:46-61` (`docker exec -it icloud /bin/sh -c "icloud --username=<icloud-username> --session-directory=/app/session_data"`, plus `--region=china` where applicable — flags verified in the icloudpy 0.5.0 CLI, `icloudpy/cmdline.py`).

## Failure modes

- **Partial downloads.** A failed download writes a truncated file (the destination is opened for writing before the transfer, `src/sync_drive.py:195-198`) and returns `False` after logging (`src/sync_drive.py:203-205`). The remote mtime is only stamped *after* a complete transfer (`src/sync_drive.py:201-202`), so a partial file's mtime mismatches the remote and the next cycle re-downloads it. Self-healing, but expect the file to be incomplete in the interim.
- **No checksum verification anywhere.** The code compares mtime + size (drive, `src/sync_drive.py:131-135`) and size only (photos, `src/sync_photos.py:68-70`). There is no hash check of downloaded content; integrity relies on the HTTPS transport. A size-preserving corruption on either side would go unnoticed.
- **Silent per-item failures.** Inside `sync_directory`, per-item exceptions are caught and swallowed to keep the loop alive (`src/sync_drive.py:288-290, 309-311`) — an item that fails during recursion is skipped without an error log. Only download-level errors are logged (`src/sync_drive.py:204`, `src/sync_photos.py:92`).
- **2FA expiry.** When the session needs interactive 2FA, the cycle logs the error, sends (at most one per 24 h) a notification email (`src/notify.py:20-23`), sleeps `retry_login_interval` (default 600 s, `src/config_parser.py:54-66`) and retries (`src/sync.py:96-106`). During this window no new data is written locally.
- **Missing password.** If the keyring holds no password, the same notify-and-retry path runs (`src/sync.py:107-118`).
- **`remove_obsolete` is a destructive mirror switch.** With `drive.remove_obsolete: true`, any local file or directory absent from the remote listing is deleted at the top level of the drive destination (`src/sync_drive.py:230-245`, invoked at 312-313); photos likewise (`src/sync_photos.py:144-156`, invoked at 202-203). It ships **false** in the sample config (`config.yaml:30, 46`). If you enable it, your local tree will eventually mirror the remote exactly — a file deleted in iCloud (while the container was down, then restored from backup) will be deleted locally too.
- **Nothing-to-sync misconfiguration.** With neither `drive:` nor `photos:` sections, the loop warns and does nothing (`src/sync.py:92-95`).

## Credentials and session data must never be committed

The iCloud username, app-specific password (`ENV_ICLOUD_PASSWORD`), the contents of `session_data/` (cookies + session JSON — a bearer credential for the whole account), and SMTP credentials in `config.yaml` (`src/config_parser.py:126-204`) are all secrets. The repo's `.gitignore` already excludes `session_data/` and `session/` (`.gitignore:137-138`) and `*.log` (`.gitignore:59`); keep it that way. Do not back these up into git, tickets, or logs — restore them from your secret store.
