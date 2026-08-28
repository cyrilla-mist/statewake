import unittest
from unittest.mock import patch

from app.models.memory import MemoryType, ProjectMemory
from app.models.reentry import OverallValidity, ValidityResult
from app.services.decision_gate import (
    DecisionGateAuthorizationError,
    DecisionGateService,
)
from app.tools.project_memory import get_project_memory


RULE = ProjectMemory(
    memory_id="memory-01",
    project_id="statewake-demo",
    memory_type=MemoryType.INTERPRETATION_RULE,
    content="Experimental implementation does not imply approved scope.",
)


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 1,
}


class ProjectMemoryTest(unittest.TestCase):
    def test_memory_can_be_read(self):
        repository = type(
            "FakeMemoryRepository",
            (),
            {"get_interpretation_rules": lambda self, project_id: [RULE]},
        )()

        with patch(
            "app.tools.project_memory.MemoryRepository",
            return_value=repository,
        ):
            result = get_project_memory()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source"], "collaboration_memory")
        self.assertEqual(result["memory"][0]["content"], RULE.content)

    def test_memory_read_does_not_change_trusted_state(self):
        trusted_state_before = dict(TRUSTED_STATE)
        writes: list[object] = []

        repository = type(
            "FakeMemoryRepository",
            (),
            {
                "get_interpretation_rules": (
                    lambda self, project_id: [RULE]
                ),
            },
        )()

        with patch(
            "app.tools.project_memory.MemoryRepository",
            return_value=repository,
        ):
            get_project_memory()

        self.assertEqual(TRUSTED_STATE, trusted_state_before)
        self.assertEqual(writes, [])

    def test_memory_cannot_authorize_prepare_resume_state(self):
        memory_result = {
            "status": "success",
            "memory": [RULE.model_dump(mode="json")],
        }
        validity = ValidityResult(
            overall_validity=OverallValidity.INVALID,
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=False,
        )

        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            with self.assertRaises(DecisionGateAuthorizationError):
                DecisionGateService().evaluate(
                    validity=validity,
                    trusted_state=TRUSTED_STATE,
                    authorized_recovery_session=memory_result,
                )

        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
