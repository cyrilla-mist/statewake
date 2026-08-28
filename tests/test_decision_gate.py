import unittest
from unittest.mock import patch

from app.models.reentry import OverallValidity, ValidityResult
from app.services.decision_gate import (
    DecisionGateAuthorizationError,
    DecisionGateService,
)


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 1,
    "direction": "Feature A",
}


AUTHORIZED_SESSION = {
    "project_id": "statewake-demo",
    "session_id": "session-hero-01",
    "status": "READY_TO_COMMIT",
    "expected_state_version": 1,
    "approved_resolution_id": "MOVE_FORWARD_WITH_B",
    "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B"],
}


def validity(overall_validity: OverallValidity) -> ValidityResult:
    return ValidityResult(
        overall_validity=overall_validity,
        previous_next_action_valid=False,
        direction_conflict=True,
        clarification_required=overall_validity == OverallValidity.AMBIGUOUS,
    )


class DecisionGateTest(unittest.TestCase):
    def setUp(self):
        self.gate = DecisionGateService()

    def test_valid_does_not_mutate(self):
        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            result = self.gate.evaluate(
                validity(OverallValidity.VALID),
                TRUSTED_STATE,
            )

        prepare.assert_not_called()
        self.assertEqual(result["decision"], "aligned")
        self.assertFalse(result["mutated"])

    def test_invalid_authorized_recovery(self):
        committed = {
            "status": "COMMITTED",
            "checkpoint_id": "CP-02",
        }

        with patch(
            "app.services.decision_gate.prepare_resume_state",
            return_value=committed,
        ) as prepare:
            result = self.gate.evaluate(
                validity(OverallValidity.INVALID),
                TRUSTED_STATE,
                AUTHORIZED_SESSION,
            )

        prepare.assert_called_once_with(
            project_id="statewake-demo",
            session_id="session-hero-01",
            expected_state_version=1,
            approved_resolution_id="MOVE_FORWARD_WITH_B",
        )
        self.assertEqual(result["decision"], "recovery_required")
        self.assertTrue(result["mutated"])
        self.assertEqual(result["resume_state"], committed)

    def test_ambiguous_requires_one_question_and_does_not_mutate(self):
        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            result = self.gate.evaluate(
                validity(OverallValidity.AMBIGUOUS),
                TRUSTED_STATE,
            )

        prepare.assert_not_called()
        self.assertEqual(result["decision"], "clarification_required")
        self.assertFalse(result["mutated"])
        self.assertIsInstance(result["authorization_question"], str)
        self.assertTrue(result["authorization_question"].endswith("?"))

    def test_invalid_without_authorization_does_not_call_writer(self):
        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            with self.assertRaises(DecisionGateAuthorizationError):
                self.gate.evaluate(
                    validity(OverallValidity.INVALID),
                    TRUSTED_STATE,
                )

        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
