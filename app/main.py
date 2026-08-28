from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent.validity_agent import (
    parse_validity_response,
    root_agent,
)
from app.config import (
    ADK_APP_NAME,
    ADK_USER_ID,
)
from app.tools.project_memory import get_project_memory


USER_RETURN_MESSAGE = (
    "I am returning to this project after being away. Check whether my "
    "trusted working state is still safe to continue from."
)

logger = logging.getLogger(__name__)
MAX_ADK_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (2.0, 5.0)
MAX_EXPLICIT_RETRY_DELAY_SECONDS = 30.0


def _retry_hint_seconds(exc: Exception) -> float | None:
    """Return a bounded provider retry hint, if one is available."""

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after is not None:
        try:
            return min(float(retry_after), MAX_EXPLICIT_RETRY_DELAY_SECONDS)
        except (TypeError, ValueError):
            pass

    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        error_details = details.get("error", details)
        retry_delay = (
            error_details.get("retryDelay")
            if isinstance(error_details, dict)
            else None
        )
        if isinstance(retry_delay, str) and retry_delay.endswith("s"):
            retry_delay = retry_delay[:-1]
        try:
            if retry_delay is not None:
                return min(float(retry_delay), MAX_EXPLICIT_RETRY_DELAY_SECONDS)
        except (TypeError, ValueError):
            pass

    return None


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Recognize only temporary Gemini/API infrastructure failures."""

    code = getattr(exc, "code", None)
    status = str(getattr(exc, "status", "")).upper()
    message = str(exc).upper()

    if code == 503 or status == "UNAVAILABLE" or "503 UNAVAILABLE" in message:
        return True

    if code == 429 or status == "RESOURCE_EXHAUSTED" or "429" in message:
        return _retry_hint_seconds(exc) is not None

    return False


def _retry_delay(exc: Exception, attempt: int) -> float:
    explicit = _retry_hint_seconds(exc)
    if explicit is not None:
        return explicit
    return RETRY_DELAYS_SECONDS[min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)]


async def _run_adk_attempt(*, message: types.Content) -> str:
    """Run one isolated ADK attempt with a fresh runtime session."""

    session_service = InMemorySessionService()
    adk_runtime_session_id = f"adk-return-{uuid4().hex}"

    try:
        await session_service.create_session(
            app_name=ADK_APP_NAME,
            user_id=ADK_USER_ID,
            session_id=adk_runtime_session_id,
        )
    except Exception as exc:
        raise RuntimeError(
            "ADK User Return runtime session creation failed."
        ) from exc

    runner = Runner(
        agent=root_agent,
        app_name=ADK_APP_NAME,
        session_service=session_service,
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=ADK_USER_ID,
        session_id=adk_runtime_session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content:
            parts = event.content.parts or []
            final_text = "".join(
                part.text or ""
                for part in parts
                if getattr(part, "text", None)
            ).strip()

    if not final_text:
        raise ValueError("The ADK agent returned no final validity response.")
    return final_text


async def run_user_return() -> dict:
    """Run one production STATEWAKE User Return assessment."""

    if not ADK_APP_NAME or not ADK_USER_ID:
        raise RuntimeError(
            "ADK app and user settings are required."
        )

    message = types.Content(
        role="user",
        parts=[types.Part(text=USER_RETURN_MESSAGE)],
    )

    final_text = ""
    for attempt in range(1, MAX_ADK_ATTEMPTS + 1):
        try:
            final_text = await _run_adk_attempt(message=message)
            break
        except Exception as exc:
            if not _is_transient_gemini_error(exc):
                if str(exc).startswith("ADK User Return runtime session"):
                    raise
                raise RuntimeError(
                    "Gemini User Return execution failed."
                ) from exc
            if attempt == MAX_ADK_ATTEMPTS:
                logger.error(
                    "Gemini User Return failed after %s transient attempts: %s",
                    attempt,
                    type(exc).__name__,
                )
                raise RuntimeError(
                    "Temporary Gemini infrastructure failure after bounded retries."
                ) from exc
            delay = _retry_delay(exc, attempt)
            logger.warning(
                "Transient Gemini failure on attempt %s/%s (%s); retrying in %.1fs",
                attempt,
                MAX_ADK_ATTEMPTS,
                type(exc).__name__,
                delay,
            )
            await asyncio.sleep(delay)

    try:
        validity = parse_validity_response(final_text)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "The ADK agent returned malformed validity output."
        ) from exc

    memory_context = get_project_memory()
    applied_memory = [
        {
            "memory_id": memory.get("memory_id"),
            "memory_type": memory.get("memory_type"),
            "authority": memory.get("authority"),
            "summary": memory.get("content"),
        }
        for memory in memory_context.get("memory", [])
        if memory.get("active", True)
    ]

    return {
        "status": "success",
        "validity": validity.model_dump(mode="json"),
        "raw_response": final_text,
        "applied_memory": applied_memory,
    }


async def main() -> dict:
    return await run_user_return()


if __name__ == "__main__":
    print(asyncio.run(main()))
