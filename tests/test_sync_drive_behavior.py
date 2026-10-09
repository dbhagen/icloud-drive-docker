"""Behavior tests for sync_drive error handling and change-detection semantics."""
__author__ = "Obvious <obvious@obvious.ai>"

import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from icloudpy.exceptions import ICloudPyAPIResponseException

import tests
from src import read_config, sync_drive
from tests import data


class PartialDownloadResponse:
    """Simulates a download response that drops the connection mid-transfer."""

    def __init__(self):
        self.url = "https://icloud-content.com/download"

    def __enter__(self):
        """Enter the context like a real response object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Propagate exceptions like a real context manager."""
        return False

    def iter_content(self, chunk_size):
        """Write one chunk, then fail like a dropped connection."""
        yield b"partial-bytes"
        raise ICloudPyAPIResponseException("Connection dropped mid-transfer")


class TestSyncDriveBehavior(unittest.TestCase):
    """Behavior tests for sync_drive.py file."""

    def setUp(self) -> None:
        """Initialize tests."""
        self.config = read_config(config_path=tests.CONFIG_PATH)
        self.filters = self.config["drive"]["filters"]
        self.ignore = self.config["drive"]["ignore"]
        self.root = tests.DRIVE_DIR
        self.destination_path = self.root
        os.makedirs(self.destination_path, exist_ok=True)
        self.service = data.ICloudPyServiceMock(
            data.AUTHENTICATED_USER, data.VALID_PASSWORD
        )
        self.drive = self.service.drive
        self.items = self.drive.dir()
        self.file_item = self.drive[self.items[4]]["Test"]["Scanned document 1.pdf"]
        self.file_name = "Scanned document 1.pdf"
        self.local_file_path = os.path.join(self.destination_path, self.file_name)

    def tearDown(self) -> None:
        """Delete temp directory."""
        shutil.rmtree(tests.TEMP_DIR)

    def process_file(self, files):
        """Process the synthetic file item once."""
        return sync_drive.process_file(
            item=self.file_item,
            destination_path=self.destination_path,
            filters=self.filters["file_extensions"],
            ignore=None,
            files=files,
        )

    def test_partial_download_leaves_partial_file_next_sync_recovers(self):
        """A mid-transfer failure leaves a partial file that the next sync replaces."""
        files = set()
        with patch.object(
            self.file_item, "open", return_value=PartialDownloadResponse()
        ):
            # No exception escapes the failed download ...
            self.assertTrue(self.process_file(files=files))
            # ... but the file on disk is only the partial bytes.
            with open(self.local_file_path, "rb") as partial_file:
                self.assertEqual(b"partial-bytes", partial_file.read())
        # The next sync pass re-downloads the file completely.
        self.assertTrue(self.process_file(files=files))
        self.assertEqual(self.file_item.size, os.path.getsize(self.local_file_path))

    def test_same_size_and_mtime_content_change_is_not_detected(self):
        """A same-size, same-mtime edit is skipped: detection is mtime+size, not checksum."""
        files = set()
        self.assertTrue(self.process_file(files=files))
        file_stat = os.stat(self.local_file_path)
        file_size = file_stat.st_size
        with open(self.local_file_path, "wb") as local_file:
            local_file.write(b"\x00" * file_size)
        os.utime(self.local_file_path, (file_stat.st_atime, file_stat.st_mtime))
        # Same size and mtime as the remote copy: the edit is not detected ...
        self.assertFalse(self.process_file(files=files))
        # ... and the stale content is still on disk.
        with open(self.local_file_path, "rb") as stale_file:
            self.assertEqual(b"\x00" * file_size, stale_file.read())

    def run_top_sync(self, remove):
        """Run a top-level drive sync against the synthetic service mock."""
        return sync_drive.sync_directory(
            drive=self.drive,
            destination_path=self.destination_path,
            items=self.items,
            root=self.root,
            top=True,
            filters=self.filters,
            ignore=self.ignore,
            remove=remove,
        )

    def test_remote_deleted_file_removed_only_with_remove_true(self):
        """A local file the remote no longer has is kept unless remove is true."""
        self.run_top_sync(remove=False)
        synced_file = next(
            path for path in Path(self.destination_path).rglob("*") if path.is_file()
        )
        stray_file = synced_file.parent / "stray.txt"
        stray_file.write_text("stray content", encoding="utf-8")

        # Default: the stray file survives the next sync.
        self.run_top_sync(remove=False)
        self.assertTrue(stray_file.exists())
        self.assertTrue(synced_file.exists())

        # remove=True: the stray file is removed, synced files are untouched.
        self.run_top_sync(remove=True)
        self.assertFalse(stray_file.exists())
        self.assertTrue(synced_file.exists())
