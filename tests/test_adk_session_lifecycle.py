import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import run_user_return


VALID_RESPONSE = "\n".join(
    [
        "OVERALL_VALIDITY: VALID",
        "PREVIOUS_NEXT_ACTION_VALID: YES",
        "DIRECTION_CONFLICT: NO",
        "CLARIFICATION_REQUIRED: NO",
    ]
)


class FakeSessionService:
    instances = []

    def __init__(self):
        self.created = []
        self.__class__.instances.append(self)

    async def create_session(self, **kwargs):
        self.created.append(kwargs)


class FakeRunner:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        self.__class__.instances.append(self)

    def run_async(self, **kwargs):
        self.calls.append(kwargs)

        async def events():
            yield SimpleNamespace(
                is_final_response=lambda: True,
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text=VALID_RESPONSE)]
                ),
            )

        return events()


class AdkSessionLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeSessionService.instances.clear()
        FakeRunner.instances.clear()

    async def test_runtime_session_is_created_and_used_by_same_runner(self):
        with (
            patch("app.main.InMemorySessionService", FakeSessionService),
            patch("app.main.Runner", FakeRunner),
            patch("app.main.get_project_memory", return_value={"memory": []}),
        ):
            result = await run_user_return()

        session = FakeSessionService.instances[0]
        runner = FakeRunner.instances[0]
        created_id = session.created[0]["session_id"]

        self.assertEqual(result["status"], "success")
        self.assertIs(runner.kwargs["session_service"], session)
        self.assertEqual(runner.calls[0]["session_id"], created_id)
        self.assertEqual(runner.calls[0]["user_id"], session.created[0]["user_id"])

    async def test_sequential_invocations_use_distinct_runtime_sessions(self):
        with (
            patch("app.main.InMemorySessionService", FakeSessionService),
            patch("app.main.Runner", FakeRunner),
            patch("app.main.get_project_memory", return_value={"memory": []}),
        ):
            await run_user_return()
            await run_user_return()

        ids = [
            instance.created[0]["session_id"]
            for instance in FakeSessionService.instances
        ]
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual(
            [runner.calls[0]["session_id"] for runner in FakeRunner.instances],
            ids,
        )

    async def test_runtime_session_failure_fails_closed(self):
        class FailingSessionService(FakeSessionService):
            async def create_session(self, **kwargs):
                raise RuntimeError("session create failed")

        with patch("app.main.InMemorySessionService", FailingSessionService):
            with self.assertRaisesRegex(RuntimeError, "runtime session"):
                await run_user_return()


if __name__ == "__main__":
    unittest.main()
