import unittest
from unittest.mock import AsyncMock, patch

from app.models.reentry import ValidityResult
from app.services.decision_gate import DecisionGateService
from app.workflows.reentry_flow import run_reentry_flow


TRUSTED_STATE_RESULT = {
    "status": "success",
    "project_state": {
        "project_id": "statewake-demo",
        "stateVersion": 1,
        "checkpoint_id": "CP-01",
        "evidence_cursor": "baseline",
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


def ambiguous_result():
    return {
        "status": "success",
        "validity": {
            "overall_validity": "AMBIGUOUS",
            "previous_next_action_valid": False,
            "direction_conflict": True,
            "clarification_required": True,
        },
        "raw_response": "agent result",
    }


class AuthorizedRecoveryTest(unittest.IsolatedAsyncioTestCase):
    @patch("app.workflows.reentry_flow.get_project_state", return_value=TRUSTED_STATE_RESULT)
    @patch("app.workflows.reentry_flow.run_user_return", new_callable=AsyncMock)
    async def test_ambiguous_stays_non_mutating_before_authorization(self, run_user_return, get_state):
        run_user_return.return_value = ambiguous_result()
        with patch("app.services.decision_gate.prepare_resume_state") as writer:
            result = await run_reentry_flow()
        writer.assert_not_called()
        self.assertEqual(result["validity"]["overall_validity"], "AMBIGUOUS")
        self.assertNotIn("resume_state", result)

    def test_authorized_ambiguity_delegates_to_writer(self):
        committed = {"status": "COMMITTED", "checkpoint_id": "CP-02", "stateVersion": 2}
        validity = ValidityResult(
            overall_validity="AMBIGUOUS",
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=True,
        )
        with patch("app.services.decision_gate.prepare_resume_state", return_value=committed) as writer:
            result = DecisionGateService().commit_authorized_resolution(
                validity, TRUSTED_STATE_RESULT["project_state"], AUTHORIZED_SESSION
            )
        writer.assert_called_once_with(
            project_id="statewake-demo",
            session_id="session-hero-01",
            expected_state_version=1,
            approved_resolution_id="MOVE_FORWARD_WITH_B",
        )
        self.assertEqual(result["resume_state"], committed)
        self.assertTrue(result["mutated"])

    def test_repeated_commit_result_is_reported_idempotently(self):
        already = {"status": "ALREADY_COMMITTED", "checkpoint_id": "CP-02", "stateVersion": 2}
        validity = ValidityResult(
            overall_validity="AMBIGUOUS",
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=True,
        )
        with patch("app.services.decision_gate.prepare_resume_state", return_value=already):
            result = DecisionGateService().commit_authorized_resolution(
                validity, TRUSTED_STATE_RESULT["project_state"], AUTHORIZED_SESSION
            )
        self.assertFalse(result["mutated"])
        self.assertEqual(result["resume_state"]["status"], "ALREADY_COMMITTED")

    def test_completed_session_can_replay_idempotently(self):
        already = {"status": "ALREADY_COMMITTED", "checkpoint_id": "CP-02"}
        completed_session = {**AUTHORIZED_SESSION, "status": "COMPLETED"}
        validity = ValidityResult(
            overall_validity="VALID",
            previous_next_action_valid=True,
            direction_conflict=False,
            clarification_required=False,
        )
        with patch("app.services.decision_gate.prepare_resume_state", return_value=already) as writer:
            result = DecisionGateService().commit_authorized_resolution(
                validity.model_copy(update={"overall_validity": "AMBIGUOUS"}),
                TRUSTED_STATE_RESULT["project_state"],
                completed_session,
            )
        writer.assert_called_once()
        self.assertEqual(result["resume_state"]["status"], "ALREADY_COMMITTED")


if __name__ == "__main__":
    unittest.main()
