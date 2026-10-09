"""Behavior tests for read_config failure surfacing and normalization."""
__author__ = "Obvious <obvious@obvious.ai>"

import os
import shutil
import unittest

from ruamel.yaml import YAMLError

import tests
from src import read_config


class TestReadConfigErrors(unittest.TestCase):
    """Tests for read_config failure and normalization behavior."""

    def setUp(self) -> None:
        """Initialize tests."""
        os.makedirs(tests.TEMP_DIR, exist_ok=True)

    def tearDown(self) -> None:
        """Delete temp directory."""
        shutil.rmtree(tests.TEMP_DIR)

    def test_read_config_invalid_yaml_raises_yaml_error(self):
        """A syntactically invalid config file raises a YAML error."""
        config_path = os.path.join(tests.TEMP_DIR, "invalid-syntax-config.yaml")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write("\tthis is: not: valid: yaml [")
        with self.assertRaises(YAMLError):
            read_config(config_path=config_path)

    def test_read_config_missing_required_keys_raises_key_error(self):
        """A config file missing app > credentials > username raises KeyError."""
        config_path = os.path.join(tests.TEMP_DIR, "missing-keys-config.yaml")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write("photos:\n  filters:\n    albums: []\n")
        with self.assertRaises(KeyError):
            read_config(config_path=config_path)

    def test_read_config_strips_username_whitespace(self):
        """Username whitespace is stripped when the config is read."""
        config_path = os.path.join(tests.TEMP_DIR, "padded-username-config.yaml")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write('app:\n  credentials:\n    username: "  user@icloud.com  "\n')
        config = read_config(config_path=config_path)
        self.assertEqual("user@icloud.com", config["app"]["credentials"]["username"])

    def test_read_config_null_username_becomes_empty_string(self):
        """A null username is normalized to the empty string."""
        config_path = os.path.join(tests.TEMP_DIR, "null-username-config.yaml")
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write("app:\n  credentials:\n    username:\n")
        config = read_config(config_path=config_path)
        self.assertEqual("", config["app"]["credentials"]["username"])
