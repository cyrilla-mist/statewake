import unittest
from unittest.mock import patch

from app.agent.validity_agent import (
    VALIDITY_AGENT_INSTRUCTION,
    parse_validity_response,
    root_agent,
)
from app.models.memory import MemoryType, ProjectMemory
from app.models.reentry import OverallValidity, ValidityResult
from app.services.decision_gate import (
    DecisionGateAuthorizationError,
    DecisionGateService,
)
from app.tools.project_memory import get_project_memory


class AgentWiringTest(unittest.TestCase):
    def test_agent_registers_project_memory(self):
        tool_names = {tool.__name__ for tool in root_agent.tools}

        self.assertEqual(
            tool_names,
            {
                "get_project_state",
                "get_recent_evidence",
                "get_project_memory",
            },
        )

    def test_memory_can_be_provided_as_context(self):
        rule = ProjectMemory(
            memory_id="memory-01",
            project_id="statewake-demo",
            memory_type=MemoryType.INTERPRETATION_RULE,
            content=(
                "Experimental implementation does not imply approved scope."
            ),
        )
        fake_repository = type(
            "FakeMemoryRepository",
            (),
            {"get_interpretation_rules": lambda self, project_id: [rule]},
        )()

        with patch(
            "app.tools.project_memory.MemoryRepository",
            return_value=fake_repository,
        ):
            context = get_project_memory()

        self.assertEqual(context["memory"][0]["content"], rule.content)
        self.assertIn("Memory Interpretation Rules", VALIDITY_AGENT_INSTRUCTION)

    def test_memory_alone_cannot_make_invalid_state_valid(self):
        invalid_response = parse_validity_response(
            "\n".join(
                [
                    "OVERALL_VALIDITY: INVALID",
                    "PREVIOUS_NEXT_ACTION_VALID: NO",
                    "DIRECTION_CONFLICT: YES",
                    "CLARIFICATION_REQUIRED: NO",
                ]
            )
        )

        self.assertEqual(
            invalid_response.overall_validity,
            OverallValidity.INVALID,
        )
        self.assertIn(
            "Memory alone can never make an INVALID state VALID.",
            VALIDITY_AGENT_INSTRUCTION,
        )

    def test_memory_cannot_authorize_state_transition(self):
        validity = ValidityResult(
            overall_validity=OverallValidity.INVALID,
            previous_next_action_valid=False,
            direction_conflict=True,
            clarification_required=False,
        )
        memory_context = {
            "status": "success",
            "memory": [
                {
                    "memory_type": "interpretation_rule",
                    "content": "Experimental implementation does not imply approved scope.",
                }
            ],
        }

        with patch(
            "app.services.decision_gate.prepare_resume_state"
        ) as prepare:
            with self.assertRaises(DecisionGateAuthorizationError):
                DecisionGateService().evaluate(
                    validity=validity,
                    trusted_state={
                        "project_id": "statewake-demo",
                        "stateVersion": 1,
                    },
                    authorized_recovery_session=memory_context,
                )

        prepare.assert_not_called()
        self.assertIn(
            "Memory cannot authorize recovery",
            VALIDITY_AGENT_INSTRUCTION,
        )

    def test_unresolved_protected_conflict_is_ambiguous_with_invalid_next_action(
        self,
    ):
        response = parse_validity_response(
            "\n".join(
                [
                    "OVERALL_VALIDITY: AMBIGUOUS",
                    "PREVIOUS_NEXT_ACTION_VALID: NO",
                    "DIRECTION_CONFLICT: YES",
                    "CLARIFICATION_REQUIRED: YES",
                ]
            )
        )

        self.assertEqual(
            response.overall_validity,
            OverallValidity.AMBIGUOUS,
        )
        self.assertFalse(response.previous_next_action_valid)
        self.assertTrue(response.direction_conflict)
        self.assertTrue(response.clarification_required)
        self.assertIn(
            "Use INVALID only when the relevant invalidation is sufficiently resolved",
            VALIDITY_AGENT_INSTRUCTION,
        )
        self.assertIn(
            "AMBIGUOUS takes precedence over INVALID",
            VALIDITY_AGENT_INSTRUCTION,
        )


if __name__ == "__main__":
    unittest.main()
