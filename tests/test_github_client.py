import io
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError

from app.services.github_client import GitHubClient, GitHubRateLimitError


class FakeResponse:
    def __init__(self, payload: bytes):
        self.headers = Message()
        self.headers["X-RateLimit-Remaining"] = "42"
        self.headers["X-RateLimit-Reset"] = "1234567890"
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class GitHubClientTest(unittest.TestCase):
    def test_optional_token_adds_auth_header_without_exposing_token(self):
        token = "secret-test-token"
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse(b'{"ok": true}')

        with patch("app.services.github_client.GITHUB_TOKEN", token), patch(
            "app.services.github_client.urlopen", side_effect=fake_urlopen
        ):
            client = GitHubClient()
            self.assertEqual(client._get_json("https://api.github.com/test"), {"ok": True})

        self.assertEqual(captured["request"].headers["Authorization"], f"Bearer {token}")
        self.assertNotIn(token, repr(client.last_rate_limit))

    def test_missing_token_keeps_public_headers(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse(b'{"ok": true}')

        with patch("app.services.github_client.GITHUB_TOKEN", None), patch(
            "app.services.github_client.urlopen", side_effect=fake_urlopen
        ):
            GitHubClient()._get_json("https://api.github.com/test")

        self.assertNotIn("Authorization", captured["request"].headers)

    def test_403_rate_limit_is_classified_without_body_or_token(self):
        headers = Message()
        headers["X-RateLimit-Remaining"] = "0"
        headers["X-RateLimit-Reset"] = "9876543210"
        error = HTTPError(
            "https://api.github.com/test",
            403,
            "rate limit",
            headers,
            io.BytesIO(b"secret response body"),
        )
        with patch("app.services.github_client.urlopen", side_effect=error):
            client = GitHubClient()
            with self.assertRaises(GitHubRateLimitError) as raised:
                client._get_json("https://api.github.com/test")

        self.assertEqual(raised.exception.remaining, "0")
        self.assertEqual(raised.exception.reset, "9876543210")
        self.assertNotIn("secret response body", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
