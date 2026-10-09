"""Behavior tests for sync_photos album batching at the mocked icloudpy boundary."""
__author__ = "Obvious <obvious@obvious.ai>"

import datetime
import io
import os
import shutil
import unittest

from icloudpy.exceptions import ICloudPyAPIResponseException

import tests
from src import sync_photos


class FakeDownloadResponse:
    """Mimics an icloudpy photo download response."""

    def __init__(self, content):
        self.raw = io.BytesIO(content)


class FakePhoto:
    """Mimics an icloudpy photo with selectable version sizes."""

    def __init__(self, filename, photo_id, versions):
        self.filename = filename
        self.id = photo_id
        self.versions = versions
        self.added_date = datetime.datetime(2026, 10, 9, 12, 0, 0)
        self.download_calls = []

    def download(self, file_size):
        """Serve the requested version and record the boundary call."""
        self.download_calls.append(file_size)
        return FakeDownloadResponse(self.versions[file_size]["content"])


class BrokenPhoto(FakePhoto):
    """A photo whose download always fails at the mocked boundary."""

    def download(self, file_size):
        self.download_calls.append(file_size)
        raise ICloudPyAPIResponseException("Forbidden")


class FakeAlbum:
    """Mimics an icloudpy album: an iterable of photos plus subalbums."""

    def __init__(self, title, photos):
        self.title = title
        self.photos = photos
        self.subalbums = {}

    def __iter__(self):
        """Iterate over the photos like a real album."""
        return iter(self.photos)


class TestPhotosBatchBehavior(unittest.TestCase):
    """Behavior tests for sync_photos.py file."""

    def setUp(self) -> None:
        """Initialize tests."""
        self.destination_path = os.path.join(tests.TEMP_DIR, "Photos")
        os.makedirs(self.destination_path, exist_ok=True)

    def tearDown(self) -> None:
        """Delete temp directory."""
        shutil.rmtree(tests.TEMP_DIR)

    def test_batch_continues_when_one_photo_download_fails(self):
        """One failing photo download does not abort the remaining photos in the album."""
        broken = BrokenPhoto(
            "broken.jpeg", "broken-id", {"original": {"size": 16, "content": b""}}
        )
        healthy = FakePhoto(
            "healthy.jpeg",
            "healthy-id",
            {"original": {"size": 13, "content": b"healthy-bytes"}},
        )
        album = FakeAlbum("Album", [broken, healthy])

        self.assertTrue(
            sync_photos.sync_album(
                album=album,
                destination_path=self.destination_path,
                file_sizes=["original"],
                extensions=["jpeg"],
                files=set(),
            )
        )
        # The failing photo was attempted exactly once and produced no file.
        self.assertEqual(["original"], broken.download_calls)
        self.assertEqual(
            [], [name for name in os.listdir(self.destination_path) if "broken" in name]
        )
        # The healthy photo was still downloaded with its full content.
        downloaded_name = next(
            name for name in os.listdir(self.destination_path) if "healthy" in name
        )
        with open(
            os.path.join(self.destination_path, downloaded_name), "rb"
        ) as downloaded:
            self.assertEqual(b"healthy-bytes", downloaded.read())

    def test_one_file_per_requested_size(self):
        """Each requested file size downloads one suffixed file for the photo."""
        photo = FakePhoto(
            "IMG_0001.jpeg",
            "photo-id",
            {
                "thumb": {"size": 11, "content": b"thumb-bytes"},
                "original": {"size": 14, "content": b"original-bytes"},
            },
        )
        album = FakeAlbum("Album", [photo])

        self.assertTrue(
            sync_photos.sync_album(
                album=album,
                destination_path=self.destination_path,
                file_sizes=["thumb", "original"],
                extensions=["jpeg"],
                files=set(),
            )
        )
        downloaded_names = sorted(os.listdir(self.destination_path))
        self.assertEqual(2, len(downloaded_names))
        thumb_file = next(name for name in downloaded_names if "thumb" in name)
        original_file = next(name for name in downloaded_names if "original" in name)
        with open(os.path.join(self.destination_path, thumb_file), "rb") as thumb:
            self.assertEqual(b"thumb-bytes", thumb.read())
        with open(os.path.join(self.destination_path, original_file), "rb") as original:
            self.assertEqual(b"original-bytes", original.read())

    def test_unwanted_extension_is_not_downloaded(self):
        """Photos with unwanted extensions are skipped without a download call."""
        photo = FakePhoto(
            "IMG_0001.jpeg",
            "photo-id",
            {"original": {"size": 14, "content": b"original-bytes"}},
        )
        album = FakeAlbum("Album", [photo])

        self.assertTrue(
            sync_photos.sync_album(
                album=album,
                destination_path=self.destination_path,
                file_sizes=["original"],
                extensions=["png"],
                files=set(),
            )
        )
        self.assertEqual([], os.listdir(self.destination_path))
        self.assertEqual([], photo.download_calls)
