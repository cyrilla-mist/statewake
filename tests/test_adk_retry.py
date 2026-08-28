import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from google.genai import errors

from app.main import run_user_return


VALID_RESPONSE = "\n".join(
    [
        "OVERALL_VALIDITY: VALID",
        "PREVIOUS_NEXT_ACTION_VALID: YES",
        "DIRECTION_CONFLICT: NO",
        "CLARIFICATION_REQUIRED: NO",
    ]
)


def transient_503() -> errors.ServerError:
    return errors.ServerError(
        503,
        {"error": {"message": "temporary high demand", "status": "UNAVAILABLE"}},
        None,
    )


class RecordingSessionService:
    instances = []

    def __init__(self):
        self.created = []
        self.__class__.instances.append(self)

    async def create_session(self, **kwargs):
        self.created.append(kwargs)


class SequencedRunner:
    outcomes = []
    instances = []

    def __init__(self, **kwargs):
        self.outcome = self.__class__.outcomes.pop(0)
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    def run_async(self, **kwargs):
        self.call = kwargs

        async def events():
            if isinstance(self.outcome, Exception):
                raise self.outcome
            yield SimpleNamespace(
                is_final_response=lambda: True,
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text=self.outcome)]
                ),
            )

        return events()


class GeminiRetryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        RecordingSessionService.instances.clear()
        SequencedRunner.instances.clear()
        SequencedRunner.outcomes.clear()

    async def run_with_outcomes(self, outcomes):
        SequencedRunner.outcomes.extend(outcomes)
        with (
            patch("app.main.InMemorySessionService", RecordingSessionService),
            patch("app.main.Runner", SequencedRunner),
            patch("app.main.get_project_memory", return_value={"memory": []}),
            patch("app.main.asyncio.sleep", new_callable=AsyncMock) as sleep,
        ):
            result = await run_user_return()
        return result, sleep

    async def test_one_503_then_success(self):
        result, sleep = await self.run_with_outcomes([transient_503(), VALID_RESPONSE])
        self.assertEqual(result["status"], "success")
        sleep.assert_awaited_once_with(2.0)

    async def test_two_transient_failures_then_success(self):
        result, sleep = await self.run_with_outcomes(
            [transient_503(), transient_503(), VALID_RESPONSE]
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual([call.args[0] for call in sleep.await_args_list], [2.0, 5.0])

    async def test_retry_limit_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "Temporary Gemini infrastructure"):
            await self.run_with_outcomes(
                [transient_503(), transient_503(), transient_503()]
            )

    async def test_non_transient_error_is_not_retried(self):
        with self.assertRaisesRegex(RuntimeError, "Gemini User Return execution failed"):
            await self.run_with_outcomes([PermissionError("forbidden")])
        self.assertEqual(len(SequencedRunner.instances), 1)

    async def test_each_attempt_uses_fresh_runtime_session(self):
        await self.run_with_outcomes([transient_503(), transient_503(), VALID_RESPONSE])
        created_ids = [
            instance.created[0]["session_id"]
            for instance in RecordingSessionService.instances
        ]
        runner_ids = [instance.call["session_id"] for instance in SequencedRunner.instances]
        self.assertEqual(created_ids, runner_ids)
        self.assertEqual(len(set(created_ids)), 3)
        self.assertTrue(all(session_id.startswith("adk-return-") for session_id in created_ids))

    async def test_failed_attempts_do_not_call_writer(self):
        with patch("app.services.decision_gate.prepare_resume_state") as writer:
            with self.assertRaises(RuntimeError):
                await self.run_with_outcomes(
                    [transient_503(), transient_503(), transient_503()]
                )
        writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
