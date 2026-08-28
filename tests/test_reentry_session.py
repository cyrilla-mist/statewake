import unittest
from unittest.mock import MagicMock

from app.models.reentry import ValidityResult
from app.services.reentry_session import ReentrySessionService


class ReentrySessionTest(unittest.TestCase):
    def test_ambiguous_session_stores_bounded_server_proposal(self):
        repository = MagicMock()
        session_ref = MagicMock()
        repository.project_ref.return_value.collection.return_value.document.return_value = session_ref
        session_ref.get.return_value.exists = False
        service = ReentrySessionService(repository)
        validity = ValidityResult(
            overall_validity="AMBIGUOUS",
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=True,
        )
        evidence = {
            "current_cursor": "head-sha",
            "evidence": [{
                "id": "state:feature-b",
                "data": {"state": {"role": "primary-demo-flow"}},
            }],
        }

        session = service.create_awaiting_clarification(
            project_id="statewake-demo",
            session_id="reentry-session-01",
            expected_state_version=1,
            validity=validity,
            evidence=evidence,
        )

        self.assertEqual(session["status"], "AWAITING_CLARIFICATION")
        self.assertEqual(session["expected_state_version"], 1)
        self.assertEqual(session["staged_mutations"], None)
        self.assertEqual(
            session["bounded_options"]["MOVE_FORWARD_WITH_B"]["direction"],
            "Feature B",
        )
        session_ref.set.assert_called_once()


if __name__ == "__main__":
    unittest.main()
