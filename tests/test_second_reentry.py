import copy
import unittest
from unittest.mock import AsyncMock, patch

from app.agent.validity_agent import parse_validity_response, root_agent
from app.models.memory import MemoryType, ProjectMemory
from app.models.reentry import OverallValidity
from app.tools.project_memory import get_project_memory
from app.workflows.reentry_flow import run_reentry_flow


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 1,
    "checkpoint_id": "CP-01",
    "goal": "Ship hackathon demo",
    "direction": "Feature A",
    "current_next_action": "Finish Feature A integration",
}


FEATURE_C_EVIDENCE = {
    "status": "success",
    "source": "github",
    "evidence": [
        {
            "id": "state:feature-c",
            "kind": "code_state",
            "strength": "direct",
            "summary": "Experimental Feature C implementation exists.",
        },
        {
            "id": "docs:feature-c",
            "kind": "documentation",
            "strength": "corroborating",
            "summary": "README mentions experimental Feature C.",
        },
    ],
}


INTERPRETATION_RULE = ProjectMemory(
    memory_id="memory-second-reentry-01",
    project_id="statewake-demo",
    memory_type=MemoryType.INTERPRETATION_RULE,
    content="Experimental implementation does not imply approved scope.",
)


EXPECTED_AGENT_RESPONSE = "\n".join(
    [
        "OVERALL_VALIDITY: VALID",
        "PREVIOUS_NEXT_ACTION_VALID: YES",
        "DIRECTION_CONFLICT: NO",
        "CLARIFICATION_REQUIRED: NO",
    ]
)


class SecondReentryTest(unittest.IsolatedAsyncioTestCase):
    async def test_experimental_feature_does_not_trigger_false_recovery(self):
        trusted_state_before = copy.deepcopy(TRUSTED_STATE)
        checkpoints: list[dict] = []

        memory_repository = type(
            "FakeMemoryRepository",
            (),
            {
                "get_interpretation_rules": (
                    lambda self, project_id: [INTERPRETATION_RULE]
                ),
            },
        )()

        with patch(
            "app.tools.project_memory.MemoryRepository",
            return_value=memory_repository,
        ):
            memory_context = get_project_memory()

        self.assertEqual(
            memory_context["memory"][0]["content"],
            INTERPRETATION_RULE.content,
        )

        # Controlled evaluation fixture: the agent has received Trusted State,
        # Feature C evidence, and the interpretation rule, then emits its
        # validated four-field result.
        parsed = parse_validity_response(EXPECTED_AGENT_RESPONSE)

        self.assertEqual(parsed.overall_validity, OverallValidity.VALID)
        self.assertTrue(parsed.previous_next_action_valid)
        self.assertFalse(parsed.direction_conflict)
        self.assertFalse(parsed.clarification_required)

        tool_names = {tool.__name__ for tool in root_agent.tools}
        self.assertIn("get_project_memory", tool_names)
        self.assertEqual(FEATURE_C_EVIDENCE["evidence"][0]["id"], "state:feature-c")

        agent_result = {
            "status": "success",
            "validity": parsed.model_dump(mode="json"),
            "raw_response": EXPECTED_AGENT_RESPONSE,
        }

        trusted_state_result = {
            "status": "success",
            "source": "firestore",
            "project_state": TRUSTED_STATE,
        }

        with (
            patch(
                "app.workflows.reentry_flow.run_user_return",
                new=AsyncMock(return_value=agent_result),
            ),
            patch(
                "app.workflows.reentry_flow.get_project_state",
                return_value=trusted_state_result,
            ),
            patch(
                "app.services.decision_gate.prepare_resume_state",
            ) as prepare,
        ):
            result = await run_reentry_flow()

        prepare.assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["validity"], parsed.model_dump(mode="json"))
        self.assertEqual(result["decision"], "aligned")
        self.assertNotIn("resume_state", result)
        self.assertEqual(TRUSTED_STATE, trusted_state_before)
        self.assertEqual(checkpoints, [])


if __name__ == "__main__":
    unittest.main()
