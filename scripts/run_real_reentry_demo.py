from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from collections import deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.api_core.exceptions import (
    DeadlineExceeded,
    RetryError,
    ServiceUnavailable,
)
from google.auth import default as google_auth_default
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import firestore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from app.config import (  # noqa: E402
    DEMO_PROJECT_ID,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    FIRESTORE_PROJECTS_COLLECTION,
    GOOGLE_GENAI_USE_ENTERPRISE,
    GEMINI_MODEL,
    get_model_backend,
    validate_vertex_configuration,
)
from app.services.github_client import GitHubClient  # noqa: E402
from app.workflows.reentry_flow import run_reentry_flow  # noqa: E402


class DemoEnvironmentError(RuntimeError):
    """Raised when the real demo environment is not ready."""


class DemoPreflightTimeout(DemoEnvironmentError):
    """Raised when one external dependency exceeds its preflight budget."""


def _run_bounded(
    check_name: str,
    check,
    timeout_seconds: float = 10,
) -> None:
    results: deque[tuple[str, BaseException | None]] = deque()

    def worker() -> None:
        try:
            check()
        except BaseException as exc:  # noqa: BLE001
            results.append(("error", exc))
        else:
            results.append(("ok", None))

    thread = threading.Thread(
        target=worker,
        name=f"statewake-preflight-{check_name.lower()}",
        daemon=True,
    )
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        print(f"{check_name} access: TIMEOUT")
        raise DemoPreflightTimeout(
            f"{check_name} preflight exceeded {timeout_seconds:g} seconds."
        )

    status, error = results[0]
    if status == "error":
        print(f"{check_name} access: FAIL")
        raise DemoEnvironmentError(
            f"{check_name} preflight failed: {error}"
        ) from error

    print(f"{check_name} access: PASS")


def _validate_vertex_configuration() -> None:
    try:
        validate_vertex_configuration()
    except RuntimeError as exc:
        raise DemoEnvironmentError(str(exc)) from exc
    try:
        google_auth_default()
    except DefaultCredentialsError as exc:
        raise DemoEnvironmentError(
            "Application Default Credentials are unavailable for Vertex AI."
        ) from exc


def _validate_firestore() -> None:
    """Perform one direct, read-only Firestore readiness read."""

    google_auth_default()
    if not GOOGLE_CLOUD_PROJECT:
        raise DemoEnvironmentError("Firestore project is not configured.")

    db = firestore.Client(project=GOOGLE_CLOUD_PROJECT)
    snapshot = (
        db.collection(FIRESTORE_PROJECTS_COLLECTION)
        .document(DEMO_PROJECT_ID)
        .get(timeout=15)
    )
    if not snapshot.exists:
        raise DemoEnvironmentError(
            f"Firestore project document is missing: {DEMO_PROJECT_ID}."
        )


def _is_transient_firestore_error(exc: BaseException) -> bool:
    return isinstance(exc, (DeadlineExceeded, ServiceUnavailable, RetryError))


def _validate_firestore_with_retry() -> None:
    """Retry only transient direct-read failures, at most three times."""

    max_attempts = 3
    delays = (0.5, 1.0)

    for attempt in range(1, max_attempts + 1):
        try:
            _validate_firestore()
        except BaseException as exc:  # noqa: BLE001
            if not _is_transient_firestore_error(exc):
                print("Firestore access: FAIL")
                if isinstance(exc, DemoEnvironmentError):
                    raise
                raise DemoEnvironmentError(
                    "Firestore preflight failed."
                ) from exc

            if attempt == max_attempts:
                print("Firestore access: FAIL")
                raise DemoPreflightTimeout(
                    "Firestore preflight failed after bounded transient retries."
                ) from exc

            print(
                f"Firestore access: TRANSIENT RETRY "
                f"{attempt}/{max_attempts}"
            )
            time.sleep(delays[attempt - 1])
        else:
            print("Firestore access: PASS")
            return


def _validate_github() -> None:
    GitHubClient().get_branch_head_sha()


def validate_environment() -> None:
    """Validate Gemini configuration, then bounded Firestore/GitHub access."""

    print("PREFLIGHT")
    print(f"Model backend: {get_model_backend()}")
    print(
        "GOOGLE_GENAI_USE_ENTERPRISE: "
        f"{'enabled' if GOOGLE_GENAI_USE_ENTERPRISE else 'disabled'}"
    )
    print(f"Project: {GOOGLE_CLOUD_PROJECT or 'missing'}")
    print(f"Location: {GOOGLE_CLOUD_LOCATION or 'missing'}")
    print(f"Model: {GEMINI_MODEL}")
    try:
        _validate_vertex_configuration()
    except DemoEnvironmentError as exc:
        print("ADC: FAIL" if "Application Default Credentials" in str(exc) else "ADC: NOT CHECKED")
        raise exc
    else:
        print("ADC: PASS")

    _validate_firestore_with_retry()
    _run_bounded("GitHub", _validate_github, timeout_seconds=10)


def _yes_no(value: Any) -> str:
    if isinstance(value, bool):
        return "YES" if value else "NO"
    return str(value)


def is_dry_run() -> bool:
    return os.getenv("STATEWAKE_DRY_RUN", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def print_result(result: Mapping[str, Any]) -> None:
    validity = result["validity"]

    print("STATEWAKE RE-ENTRY RESULT")
    print()
    print("-------------------------")
    print("VALIDITY")
    print("-------------------------")
    print()
    print(f"OVERALL_VALIDITY: {validity['overall_validity']}")
    print(
        "PREVIOUS_NEXT_ACTION_VALID: "
        f"{_yes_no(validity['previous_next_action_valid'])}"
    )
    print(
        "DIRECTION_CONFLICT: "
        f"{_yes_no(validity['direction_conflict'])}"
    )
    print(
        "CLARIFICATION_REQUIRED: "
        f"{_yes_no(validity['clarification_required'])}"
    )
    print()
    print("-------------------------")
    print("DECISION")
    print("-------------------------")
    print()
    print(f"status: {result['status']}")
    print(f"message: {result['user_message']}")

    resume_state = result.get("resume_state")
    if resume_state is None:
        return

    print()
    print("-------------------------")
    print("RESUME STATE")
    print("-------------------------")
    print()
    print(resume_state)


async def run_demo() -> dict[str, Any]:
    validate_environment()
    return await run_reentry_flow(dry_run=is_dry_run())


def main() -> int:
    try:
        result = asyncio.run(run_demo())
    except DemoEnvironmentError as exc:
        print(f"STATEWAKE RE-ENTRY ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        message = str(exc)
        upper_message = message.upper()

        if "429" in message or "RESOURCE_EXHAUSTED" in upper_message:
            print(
                "STATEWAKE RE-ENTRY ERROR: Gemini quota or rate limit "
                "reached.",
                file=sys.stderr,
            )
        elif isinstance(exc, (DefaultCredentialsError, GoogleAPICallError)):
            print(
                "STATEWAKE RE-ENTRY ERROR: Firestore or Google Cloud "
                "connection failed.",
                file=sys.stderr,
            )
        else:
            print(
                f"STATEWAKE RE-ENTRY ERROR: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        return 1

    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
