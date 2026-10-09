"""Behavior tests for notify.py retry semantics after a failed send."""
__author__ = "Obvious <obvious@obvious.ai>"

import unittest
from unittest.mock import patch

from src import notify


class TestNotifyBehavior(unittest.TestCase):
    """Tests for notify.py file."""

    def setUp(self) -> None:
        """Initialize tests."""
        self.config = {
            "app": {
                "smtp": {
                    "email": "user@test.com",
                    "to": "to@email.com",
                    "host": "smtp.test.com",
                    "port": "587",
                    "password": "password",
                }
            }
        }

    def test_failed_send_is_retried_on_next_call(self):
        """A failed send is not throttled: the next call attempts delivery again."""
        with patch("smtplib.SMTP") as smtp:
            instance = smtp.return_value
            instance.sendmail.side_effect = Exception("connection dropped")

            self.assertIsNone(notify.send(self.config))
            self.assertIsNone(notify.send(self.config))

            self.assertEqual(2, instance.sendmail.call_count)
