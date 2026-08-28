import unittest
from unittest.mock import AsyncMock, patch

from app.workflows.reentry_flow import run_reentry_flow


CP02 = {
    "project_state": {
        "project_id": "statewake-demo",
        "stateVersion": 2,
        "checkpoint_id": "CP-02",
        "direction": "Feature B",
        "priority": "Demo clarity",
        "current_next_action": "Resolve Cloud Run deployment failure",
    }
}


class SecondReentryTraceTest(unittest.IsolatedAsyncioTestCase):
    async def test_memory_trace_preserves_cp02_without_writer(self):
        agent_result = {
            "status": "success",
            "validity": {
                "overall_validity": "VALID",
                "previous_next_action_valid": True,
                "direction_conflict": False,
                "clarification_required": False,
            },
            "raw_response": "four fields",
            "applied_memory": [{
                "memory_id": "memory-second-reentry-01",
                "memory_type": "interpretation_rule",
                "authority": "explicit_user",
                "summary": "Experimental implementation alone does not establish approved scope without explicit confirmation.",
            }],
        }
        with patch(
            "app.workflows.reentry_flow.run_user_return",
            new_callable=AsyncMock,
            return_value=agent_result,
        ), patch(
            "app.workflows.reentry_flow.get_project_state",
            return_value=CP02,
        ), patch(
            "app.services.decision_gate.prepare_resume_state",
        ) as writer:
            result = await run_reentry_flow()

        self.assertEqual(result["validity"]["overall_validity"], "VALID")
        self.assertEqual(result["decision"], "aligned")
        self.assertEqual(result["applied_memory"][0]["authority"], "explicit_user")
        self.assertEqual(CP02["project_state"]["stateVersion"], 2)
        self.assertEqual(CP02["project_state"]["checkpoint_id"], "CP-02")
        self.assertEqual(CP02["project_state"]["direction"], "Feature B")
        self.assertEqual(
            CP02["project_state"]["current_next_action"],
            "Resolve Cloud Run deployment failure",
        )
        writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
