from __future__ import annotations

import base64
import json
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.config import (
    GITHUB_BRANCH,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_TOKEN,
)


class GitHubRateLimitError(RuntimeError):
    """GitHub rejected a request because the API rate limit was reached."""

    def __init__(self, message: str, *, remaining: str | None, reset: str | None):
        super().__init__(message)
        self.remaining = remaining
        self.reset = reset


class GitHubClient:
    """
    Minimal read-only GitHub adapter for the STATEWAKE MVP.

    The MVP intentionally reads one configured public repository.
    No OAuth, write access, arbitrary URL fetching, or repository mutation.
    """

    def __init__(
        self,
        *,
        owner: str = GITHUB_OWNER,
        repo: str = GITHUB_REPO,
        branch: str = GITHUB_BRANCH,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.branch = branch

        self.api_root = (
            f"https://api.github.com/repos/"
            f"{self.owner}/{self.repo}"
        )
        self.last_rate_limit: dict[str, str | None] = {
            "remaining": None,
            "reset": None,
        }

    @property
    def repository(self) -> str:
        return f"{self.owner}/{self.repo}"

    def _get_json(self, url: str):
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "STATEWAKE-Hackathon-Prototype",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        request = Request(
            url,
            headers=headers,
        )

        try:
            with urlopen(request, timeout=20) as response:
                self.last_rate_limit = {
                    "remaining": response.headers.get("X-RateLimit-Remaining"),
                    "reset": response.headers.get("X-RateLimit-Reset"),
                }
                raw = response.read()
        except HTTPError as exc:
            remaining = exc.headers.get("X-RateLimit-Remaining")
            reset = exc.headers.get("X-RateLimit-Reset")
            if exc.code == 403:
                self.last_rate_limit = {
                    "remaining": remaining,
                    "reset": reset,
                }
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded; retry after the reported reset time.",
                    remaining=remaining,
                    reset=reset,
                ) from exc
            raise

        return json.loads(
            raw.decode("utf-8")
        )

    def get_branch_head_sha(self) -> str:
        data = self._get_json(
            f"{self.api_root}/branches/{self.branch}"
        )

        return data["commit"]["sha"]

    def get_file_text(
        self,
        path: str,
        *,
        ref: str,
    ) -> str:
        encoded_path = quote(
            path,
            safe="/",
        )

        data = self._get_json(
            f"{self.api_root}/contents/"
            f"{encoded_path}?ref={ref}"
        )

        if data.get("encoding") != "base64":
            raise RuntimeError(
                f"Unexpected encoding for {path}: "
                f"{data.get('encoding')}"
            )

        decoded = base64.b64decode(
            data["content"]
        )

        return decoded.decode(
            "utf-8-sig"
        )

    def get_json_file(
        self,
        path: str,
        *,
        ref: str,
    ) -> dict:
        return json.loads(
            self.get_file_text(
                path,
                ref=ref,
            )
        )

    def compare(
        self,
        *,
        base: str,
        head: str,
    ) -> dict:
        return self._get_json(
            f"{self.api_root}/compare/"
            f"{base}...{head}"
        )

    def get_open_issues(
        self,
    ) -> list[dict]:
        data = self._get_json(
            f"{self.api_root}/issues"
            "?state=open&per_page=100"
        )

        # GitHub's issue endpoint may also return PRs.
        return [
            issue
            for issue in data
            if "pull_request" not in issue
        ]
