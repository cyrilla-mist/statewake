import unittest
from unittest.mock import MagicMock, patch

from google.api_core.exceptions import DeadlineExceeded, PermissionDenied

from scripts.run_real_reentry_demo import (
    DemoEnvironmentError,
    DemoPreflightTimeout,
    _validate_firestore,
    _validate_firestore_with_retry,
)


class FirestorePreflightTest(unittest.TestCase):
    def _client_with_snapshot(self, exists=True):
        client = MagicMock()
        snapshot = MagicMock(exists=exists)
        client.collection.return_value.document.return_value.get.return_value = snapshot
        return client

    @patch("scripts.run_real_reentry_demo.google_auth_default")
    @patch("scripts.run_real_reentry_demo.firestore.Client")
    @patch("scripts.run_real_reentry_demo.GOOGLE_CLOUD_PROJECT", "statewake-agentic-2026")
    def test_first_attempt_direct_read_succeeds(self, client_factory, adc):
        client_factory.return_value = self._client_with_snapshot()

        _validate_firestore()

        get = client_factory.return_value.collection.return_value.document.return_value.get
        get.assert_called_once_with(timeout=15)

    @patch("scripts.run_real_reentry_demo.time.sleep")
    @patch("scripts.run_real_reentry_demo._validate_firestore")
    def test_transient_timeout_then_success(self, check, sleep):
        check.side_effect = [DeadlineExceeded("timeout"), None]

        _validate_firestore_with_retry()

        self.assertEqual(check.call_count, 2)
        sleep.assert_called_once_with(0.5)

    @patch("scripts.run_real_reentry_demo.time.sleep")
    @patch("scripts.run_real_reentry_demo._validate_firestore")
    def test_repeated_transient_timeout_is_bounded(self, check, sleep):
        check.side_effect = DeadlineExceeded("timeout")

        with self.assertRaises(DemoPreflightTimeout):
            _validate_firestore_with_retry()

        self.assertEqual(check.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("scripts.run_real_reentry_demo._validate_firestore")
    def test_permission_error_is_not_retried(self, check):
        check.side_effect = PermissionDenied("denied")

        with self.assertRaises(DemoEnvironmentError):
            _validate_firestore_with_retry()

        check.assert_called_once_with()

    @patch("scripts.run_real_reentry_demo.firestore.Client")
    @patch("scripts.run_real_reentry_demo.google_auth_default")
    @patch("scripts.run_real_reentry_demo.GOOGLE_CLOUD_PROJECT", "statewake-agentic-2026")
    def test_missing_project_document_fails_immediately(self, adc, client_factory):
        client_factory.return_value = self._client_with_snapshot(exists=False)

        with self.assertRaises(DemoEnvironmentError):
            _validate_firestore_with_retry()

        get = client_factory.return_value.collection.return_value.document.return_value.get
        get.assert_called_once_with(timeout=15)


if __name__ == "__main__":
    unittest.main()
