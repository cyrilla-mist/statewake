import unittest
from unittest.mock import patch

from app.server import _response


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 2,
    "checkpoint_id": "CP-02",
    "direction": "Feature B",
}


class AuthorizationProjectionTest(unittest.TestCase):
    def test_ambiguous_current_session_returns_authorization(self):
        authorization = {
            "session_id": "reentry-session-02",
            "expected_state_version": 2,
        }
        result = {
            "status": "success",
            "validity": {"clarification_required": True},
            "decision": "clarification_required",
            "user_message": "Which direction?",
        }
        with patch(
            "app.server._read_authorization_context",
            return_value=authorization,
        ) as reader:
            response = _response(result, context=(TRUSTED_STATE, {"evidence": []}))

        self.assertEqual(response["authorization"], authorization)
        reader.assert_called_once_with(TRUSTED_STATE)

    def test_valid_aligned_result_has_no_authorization(self):
        result = {
            "status": "success",
            "validity": {"clarification_required": False},
            "decision": "aligned",
            "user_message": "Still aligned.",
        }
        with patch("app.server._read_authorization_context") as reader:
            response = _response(result, context=(TRUSTED_STATE, {"evidence": []}))

        self.assertIsNone(response["authorization"])
        reader.assert_not_called()

    def test_completed_historical_session_cannot_leak(self):
        result = {
            "status": "success",
            "validity": {
                "clarification_required": False,
                "overall_validity": "VALID",
            },
            "decision": "aligned",
            "user_message": "Still aligned.",
        }
        with patch(
            "app.server._read_authorization_context",
            return_value={"session_id": "reentry-session-01"},
        ) as reader:
            response = _response(result, context=(TRUSTED_STATE, {"evidence": []}))

        self.assertIsNone(response["authorization"])
        reader.assert_not_called()

    def test_hero_ambiguous_contract_remains_authorized(self):
        result = {
            "status": "success",
            "validity": {
                "overall_validity": "AMBIGUOUS",
                "previous_next_action_valid": False,
                "direction_conflict": True,
                "clarification_required": True,
            },
            "decision": "clarification_required",
            "user_message": "Which direction?",
        }
        authorization = {"session_id": "reentry-session-01"}
        with patch(
            "app.server._read_authorization_context",
            return_value=authorization,
        ):
            response = _response(result, context=(TRUSTED_STATE, {"evidence": []}))

        self.assertEqual(response["authorization"], authorization)


if __name__ == "__main__":
    unittest.main()
