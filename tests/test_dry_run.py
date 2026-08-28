import unittest
from unittest.mock import AsyncMock, patch

from app.workflows.reentry_flow import DRY_RUN_MESSAGE, run_reentry_flow


TRUSTED_STATE_RESULT = {
    "status": "success",
    "source": "firestore",
    "project_state": {
        "project_id": "statewake-demo",
        "stateVersion": 1,
        "checkpoint_id": "CP-01",
        "goal": "Ship hackathon demo",
        "direction": "Feature A",
        "priority": "Technical depth",
        "current_next_action": "Finish Feature A integration",
    },
}


AGENT_INVALID_RESULT = {
    "status": "success",
    "validity": {
        "overall_validity": "INVALID",
        "previous_next_action_valid": False,
        "direction_conflict": True,
        "clarification_required": False,
    },
    "raw_response": "agent result",
}


AUTHORIZED_SESSION = {
    "project_id": "statewake-demo",
    "session_id": "session-hero-01",
    "status": "READY_TO_COMMIT",
    "expected_state_version": 1,
    "approved_resolution_id": "MOVE_FORWARD_WITH_B",
    "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B"],
}


class DryRunTest(unittest.IsolatedAsyncioTestCase):
    @patch(
        "app.workflows.reentry_flow.get_project_state",
        return_value=TRUSTED_STATE_RESULT,
    )
    @patch(
        "app.workflows.reentry_flow.run_user_return",
        new_callable=AsyncMock,
    )
    async def test_invalid_dry_run_never_mutates(
        self,
        run_user_return,
        get_project_state,
    ):
        run_user_return.return_value = AGENT_INVALID_RESULT

        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            result = await run_reentry_flow(
                authorized_recovery_session=AUTHORIZED_SESSION,
                dry_run=True,
            )

        run_user_return.assert_awaited_once_with()
        get_project_state.assert_called_once_with()
        prepare.assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["decision"], "recovery_required")
        self.assertEqual(result["user_message"], DRY_RUN_MESSAGE)
        self.assertNotIn("resume_state", result)


if __name__ == "__main__":
    unittest.main()
