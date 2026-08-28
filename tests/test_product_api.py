import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.server import app


TRUSTED_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 1,
    "checkpoint_id": "CP-01",
    "direction": "Feature A",
    "priority": "Technical depth",
    "current_next_action": "Finish Feature A integration",
}


class ProductApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    def test_health_and_project(self, state):
        self.assertEqual(
            self.client.get("/api/health").json(),
            {"status": "ok", "product": "STATEWAKE"},
        )
        response = self.client.get("/api/project")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["project_state"], TRUSTED_STATE)

    @patch("app.server.get_recent_evidence", return_value={"evidence": []})
    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    @patch("app.server._read_authorization_context", return_value=None)
    @patch("app.server.run_reentry_flow", new_callable=AsyncMock)
    def test_valid_maps_to_aligned(self, run, auth, state, evidence):
        run.return_value = {
            "status": "success",
            "validity": {
                "overall_validity": "VALID",
                "previous_next_action_valid": True,
                "direction_conflict": False,
                "clarification_required": False,
            },
            "decision": "aligned",
            "user_message": "Still aligned.",
        }
        response = self.client.post("/api/reentry", json={"dry_run": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"]["type"], "aligned")
        run.assert_awaited_once_with(dry_run=True)

    @patch("app.server.get_recent_evidence", return_value={"evidence": []})
    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    @patch("app.server._read_authorization_context", return_value=None)
    @patch("app.server.ReentrySessionService")
    @patch("app.server.run_reentry_flow", new_callable=AsyncMock)
    def test_ambiguous_maps_to_decision_gate_without_bootstrap(
        self, run, service_class, state, evidence, auth
    ):
        run.return_value = {
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
        service = service_class.return_value
        service.create_awaiting_clarification.return_value = {
            "status": "AWAITING_CLARIFICATION"
        }
        service.public_context.return_value = {
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
        }
        response = self.client.post("/api/reentry", json={"dry_run": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"]["type"], "clarification_required")
        service.create_awaiting_clarification.assert_called_once()

    @patch("app.server.ReentrySessionService")
    def test_resolution_rejects_unknown_or_client_state(self, service_class):
        unknown = self.client.post(
            "/api/reentry/resolution",
            json={
                "project_id": "statewake-demo",
                "session_id": "reentry-session-01",
                "expected_state_version": 1,
                "approved_resolution_id": "KEEP_DIRECTION_A",
            },
        )
        self.assertEqual(unknown.status_code, 422)
        injected = self.client.post(
            "/api/reentry/resolution",
            json={
                "project_id": "statewake-demo",
                "session_id": "reentry-session-01",
                "expected_state_version": 1,
                "approved_resolution_id": "MOVE_FORWARD_WITH_B",
                "staged_mutations": {"direction": "client-controlled"},
            },
        )
        self.assertEqual(injected.status_code, 422)
        service_class.assert_not_called()

    @patch("app.server.get_project_state", return_value={"project_state": TRUSTED_STATE})
    @patch("app.server.DecisionGateService.commit_authorized_resolution")
    @patch("app.server.ReentrySessionService")
    def test_defer_preserves_state_and_does_not_call_writer(
        self, service_class, gate_commit, state
    ):
        service = service_class.return_value
        service.load.return_value = {
            "status": "AWAITING_CLARIFICATION",
            "project_id": "statewake-demo",
            "session_id": "reentry-session-01",
            "expected_state_version": 1,
            "validity": {
                "overall_validity": "AMBIGUOUS",
                "previous_next_action_valid": False,
                "direction_conflict": True,
                "clarification_required": True,
            },
            "allowed_resolution_ids": ["MOVE_FORWARD_WITH_B", "DEFER"],
        }
        service.authorize.return_value = {
            **service.load.return_value,
            "status": "DEFERRED",
            "approved_resolution_id": "DEFER",
        }
        service.public_context.return_value = {}
        response = self.client.post(
            "/api/reentry/resolution",
            json={
                "project_id": "statewake-demo",
                "session_id": "reentry-session-01",
                "expected_state_version": 1,
                "approved_resolution_id": "DEFER",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"]["type"], "deferred")
        gate_commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
