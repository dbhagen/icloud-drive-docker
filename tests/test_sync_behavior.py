"""Behavior tests for sync orchestration error surfacing and region selection."""
__author__ = "Obvious <obvious@obvious.ai>"

import os
import shutil
import unittest
from unittest.mock import patch

import tests
from src import sync, sync_photos


class FakeLibrary:
    """Mimics an icloudpy photos library holding albums by name."""

    def __init__(self, albums):
        self.albums = albums


class FakePhotos:
    """Mimics the icloudpy photos API surface."""

    def __init__(self, libraries):
        self.libraries = libraries


class TestSyncBehavior(unittest.TestCase):
    """Behavior tests for sync.py error surfacing and API region selection."""

    def setUp(self) -> None:
        """Initialize tests."""
        self.root_dir = tests.TEMP_DIR
        os.makedirs(self.root_dir, exist_ok=True)

    def tearDown(self) -> None:
        """Remove temp directories."""
        shutil.rmtree(tests.TEMP_DIR)

    def test_misconfigured_album_name_is_fatal_to_sync_photos(self):
        """An album name missing from the library raises instead of skipping."""
        config = {
            "app": {"root": self.root_dir},
            "photos": {
                "destination": "photos",
                "remove_obsolete": False,
                "filters": {
                    "libraries": None,
                    "albums": ["real-album", "no-such-album"],
                    "file_sizes": ["original"],
                    "extensions": ["jpeg"],
                },
            },
        }
        photos = FakePhotos({"PrimarySync": FakeLibrary({"real-album": None})})

        with self.assertRaises(KeyError) as context:
            sync_photos.sync_photos(config=config, photos=photos)
        self.assertEqual("no-such-album", context.exception.args[0])

    def test_china_region_uses_cn_endpoints(self):
        """The china server region selects the .com.cn service endpoints."""
        with patch("src.sync.ICloudPyService") as service:
            sync.get_api_instance(
                username="user@test.com",
                password="password",
                server_region="china",
            )
            self.assertIn(".com.cn", service.call_args.kwargs["auth_endpoint"])
            self.assertIn(".com.cn", service.call_args.kwargs["setup_endpoint"])

    def test_default_region_uses_global_endpoints(self):
        """The default server region does not use the .com.cn endpoints."""
        with patch("src.sync.ICloudPyService") as service:
            sync.get_api_instance(
                username="user@test.com",
                password="password",
            )
            self.assertNotIn(".com.cn", service.call_args.kwargs.get("auth_endpoint", ""))
            self.assertNotIn(".com.cn", service.call_args.kwargs.get("setup_endpoint", ""))
