import unittest
from unittest.mock import AsyncMock, patch

from app.workflows.reentry_flow import run_reentry_flow


TRUSTED_STATE_RESULT = {
    "status": "success",
    "source": "firestore",
    "project_state": {
        "project_id": "statewake-demo",
        "stateVersion": 1,
        "checkpoint_id": "CP-01",
        "evidence_cursor": "baseline-sha",
        "goal": "Ship the demo",
        "direction": "Feature A",
        "priority": "Technical depth",
        "current_next_action": "Finish Feature A integration",
    },
}


AUTHORIZED_SESSION = {
    "project_id": "statewake-demo",
    "session_id": "session-hero-01",
    "status": "READY_TO_COMMIT",
    "expected_state_version": 1,
    "approved_resolution_id": "MOVE_FORWARD_WITH_B",
    "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B"],
}


def agent_result(
    overall_validity: str,
    *,
    previous_next_action_valid: bool,
    direction_conflict: bool,
    clarification_required: bool,
) -> dict:
    return {
        "status": "success",
        "validity": {
            "overall_validity": overall_validity,
            "previous_next_action_valid": previous_next_action_valid,
            "direction_conflict": direction_conflict,
            "clarification_required": clarification_required,
        },
        "raw_response": "agent result",
    }


class ReentryFlowTest(unittest.IsolatedAsyncioTestCase):
    @patch(
        "app.workflows.reentry_flow.get_project_state",
        return_value=TRUSTED_STATE_RESULT,
    )
    @patch(
        "app.workflows.reentry_flow.run_user_return",
        new_callable=AsyncMock,
    )
    async def test_valid_flow(
        self,
        run_user_return,
        get_project_state,
    ):
        run_user_return.return_value = agent_result(
            "VALID",
            previous_next_action_valid=True,
            direction_conflict=False,
            clarification_required=False,
        )

        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            result = await run_reentry_flow()

        prepare.assert_not_called()
        get_project_state.assert_called_once_with()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["decision"], "aligned")
        self.assertNotIn("resume_state", result)

    @patch(
        "app.workflows.reentry_flow.get_project_state",
        return_value=TRUSTED_STATE_RESULT,
    )
    @patch(
        "app.workflows.reentry_flow.run_user_return",
        new_callable=AsyncMock,
    )
    async def test_ambiguous_flow(
        self,
        run_user_return,
        get_project_state,
    ):
        run_user_return.return_value = agent_result(
            "AMBIGUOUS",
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=True,
        )

        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            result = await run_reentry_flow()

        prepare.assert_not_called()
        self.assertEqual(result["decision"], "clarification_required")
        self.assertEqual(result["user_message"].count("?"), 1)
        self.assertNotIn("resume_state", result)

    @patch(
        "app.workflows.reentry_flow.get_project_state",
        return_value=TRUSTED_STATE_RESULT,
    )
    @patch(
        "app.workflows.reentry_flow.run_user_return",
        new_callable=AsyncMock,
    )
    async def test_invalid_authorized_recovery_flow(
        self,
        run_user_return,
        get_project_state,
    ):
        run_user_return.return_value = agent_result(
            "INVALID",
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=False,
        )
        committed = {
            "status": "COMMITTED",
            "checkpoint_id": "CP-02",
        }

        with patch(
            "app.services.decision_gate.prepare_resume_state",
            return_value=committed,
        ) as prepare:
            result = await run_reentry_flow(AUTHORIZED_SESSION)

        prepare.assert_called_once_with(
            project_id="statewake-demo",
            session_id="session-hero-01",
            expected_state_version=1,
            approved_resolution_id="MOVE_FORWARD_WITH_B",
        )
        self.assertEqual(result["decision"], "recovery_required")
        self.assertEqual(result["resume_state"], committed)
        self.assertIn("committed", result["user_message"])


if __name__ == "__main__":
    unittest.main()
