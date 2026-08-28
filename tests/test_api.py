import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.server import app


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 1,
    "checkpoint_id": "CP-01",
    "evidence_cursor": "baseline-sha",
    "goal": "Ship the demo",
    "direction": "Feature A",
    "priority": "Technical depth",
    "current_next_action": "Finish Feature A integration",
}

EVIDENCE = {
    "repository": "cyrilla-mist/statewake-demo-project",
    "current_cursor": "head-sha",
    "baseline_cursor": "baseline-sha",
    "commits_since_baseline": 3,
    "evidence": [{
        "id": "state:feature-b",
        "data": {"state": {"role": "primary-demo-flow"}},
    }],
}


def agent_result(overall: str) -> dict:
    ambiguous = overall == "AMBIGUOUS"
    return {
        "status": "success",
        "validity": {
            "overall_validity": overall,
            "previous_next_action_valid": not ambiguous,
            "direction_conflict": ambiguous,
            "clarification_required": ambiguous,
        },
        "decision": "clarification_required" if ambiguous else "aligned",
        "user_message": "A bounded STATEWAKE decision.",
    }


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.authorization_reader = patch(
            "app.server._read_authorization_context",
            return_value=None,
        )
        self.authorization_reader.start()
        self.addCleanup(self.authorization_reader.stop)

    @patch("app.server.get_recent_evidence", return_value=EVIDENCE)
    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    def test_status_and_valid_mapping(self, state, evidence):
        self.assertEqual(
            self.client.get("/api/status").json(),
            {"status": "ok", "service": "STATEWAKE"},
        )
        with patch("app.server.run_reentry_flow", new_callable=AsyncMock) as run:
            run.return_value = agent_result("VALID")
            response = self.client.post("/api/reentry")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"]["type"], "aligned")

    @patch("app.server.get_recent_evidence", return_value=EVIDENCE)
    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    def test_ambiguous_creates_awaiting_session_without_bootstrap(self, state, evidence):
        service = MagicMock()
        session = {
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "status": "AWAITING_CLARIFICATION",
            "expected_state_version": 1,
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
        }
        service.create_awaiting_clarification.return_value = session
        service.public_context.return_value = {
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
            "question": "Which direction?",
        }
        with patch("app.server.ReentrySessionService", return_value=service) as service_class, patch(
            "app.server.run_reentry_flow", new_callable=AsyncMock,
        ) as run:
            service_class.public_context.return_value = service.public_context.return_value
            run.return_value = agent_result("AMBIGUOUS")
            response = self.client.post("/api/reentry")
        self.assertEqual(response.status_code, 200)
        service.create_awaiting_clarification.assert_called_once()
        self.assertEqual(response.json()["authorization"]["expected_state_version"], 1)

    @patch(
        "app.server.get_project_state",
        side_effect=[
            {"project_state": TRUSTED_STATE},
            {"project_state": {
                **TRUSTED_STATE,
                "stateVersion": 2,
                "checkpoint_id": "CP-02",
                "direction": "Feature B",
                "priority": "Demo clarity",
                "current_next_action": "Resolve Cloud Run deployment failure",
            }},
            {"project_state": {
                **TRUSTED_STATE,
                "stateVersion": 2,
                "checkpoint_id": "CP-02",
                "direction": "Feature B",
                "priority": "Demo clarity",
                "current_next_action": "Resolve Cloud Run deployment failure",
            }},
        ],
    )
    def test_resolution_transitions_and_reaches_gate(self, state):
        service = MagicMock()
        session = {
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "status": "READY_TO_COMMIT",
            "expected_state_version": 1,
            "validity": {
                "overall_validity": "AMBIGUOUS",
                "previous_next_action_valid": False,
                "direction_conflict": True,
                "clarification_required": True,
            },
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
        }
        service.load.return_value = session
        service.authorize.return_value = session
        service.public_context.return_value = {
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
            "question": "Which direction?",
        }
        gate_result = {
            "status": "success",
            "decision": "recovery_required",
            "mutated": True,
            "resume_state": {"status": "COMMITTED", "checkpoint_id": "CP-02"},
        }
        with patch("app.server.ReentrySessionService", return_value=service), patch(
            "app.server.DecisionGateService.commit_authorized_resolution",
            return_value=gate_result,
        ) as gate:
            response = self.client.post("/api/reentry/resolution", json={
                "project_id": "statewake-demo",
                "session_id": "reentry-session-01",
                "expected_state_version": 1,
                "approved_resolution_id": "MOVE_FORWARD_WITH_B",
            })
        self.assertEqual(response.status_code, 200)
        service.authorize.assert_called_once_with(
            project_id="statewake-demo",
            session_id="reentry-session-01",
            approved_resolution_id="MOVE_FORWARD_WITH_B",
            expected_state_version=1,
        )
        gate.assert_called_once()
        payload = response.json()
        self.assertEqual(payload["resume_state"]["direction"], "Feature B")
        self.assertEqual(payload["resume_state"]["priority"], "Demo clarity")
        self.assertEqual(
            payload["resume_state"]["do_first"],
            "Resolve Cloud Run deployment failure",
        )
        self.assertEqual(payload["resume_state"]["checkpoint_id"], "CP-02")
        self.assertNotEqual(payload["resume_state"]["direction"], "Feature A")
        self.assertNotEqual(payload["resume_state"]["priority"], "Technical depth")
        self.assertNotEqual(
            payload["resume_state"]["do_first"],
            "Finish Feature A integration",
        )

    def test_client_cannot_inject_state_or_use_unknown_resolution(self):
        arbitrary = self.client.post("/api/reentry/resolution", json={
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "approved_resolution_id": "MOVE_FORWARD_WITH_B",
            "staged_mutations": {"direction": "client-controlled"},
        })
        self.assertEqual(arbitrary.status_code, 422)
        unknown = self.client.post("/api/reentry/resolution", json={
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "approved_resolution_id": "KEEP_DIRECTION_A",
        })
        self.assertEqual(unknown.status_code, 422)


if __name__ == "__main__":
    unittest.main()
