import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.server import app
from app.services.memory_repository import MemoryRepository
from app.tools.github_evidence import get_recent_evidence


CP02_STATE = {
    "project_id": "statewake-demo",
    "stateVersion": 2,
    "checkpoint_id": "CP-02",
    "evidence_cursor": "b" * 40,
    "direction": "Feature B",
    "priority": "Demo clarity",
    "current_next_action": "Resolve Cloud Run deployment failure",
}


class SecondReentryTest(unittest.TestCase):
    def test_repeated_explicit_save_is_same_memory_record_only(self):
        repository = MagicMock()
        memory_collection = repository.project_ref.return_value.collection.return_value
        service = MemoryRepository(repository=repository)

        first = service.save_explicit_interpretation_rule(
            project_id="statewake-demo", confirmed=True
        )
        second = service.save_explicit_interpretation_rule(
            project_id="statewake-demo", confirmed=True
        )

        self.assertEqual(first.memory_id, "memory-second-reentry-01")
        self.assertEqual(second.memory_id, first.memory_id)
        self.assertEqual(memory_collection.document.call_count, 2)
        self.assertEqual(memory_collection.document.call_args_list[0], memory_collection.document.call_args_list[1])
        repository.project_ref.assert_called_with("statewake-demo")
        self.assertNotIn("trustedState", str(repository.mock_calls))

    @patch("app.tools.github_evidence.GitHubClient")
    @patch("app.tools.github_evidence.get_project_state")
    def test_evidence_starts_at_current_trusted_cursor(self, state_tool, client_factory):
        state_tool.return_value = {"project_state": CP02_STATE}
        client = client_factory.return_value
        client.get_branch_head_sha.return_value = "c" * 40
        client.compare.return_value = {"ahead_by": 0, "commits": [], "files": []}
        client.get_json_file.side_effect = lambda path, ref: {
            "app/route.json": {
                "activeFeature": "feature-b",
                "route": "/demo",
                "status": "active",
            },
            "app/feature-a.json": {"id": "feature-a", "status": "inactive"},
            "app/feature-b.json": {"id": "feature-b", "status": "active"},
            "deployment/status.json": {"status": "blocked"},
            "app/presentation.json": {"behaviorChanged": False},
        }[path]
        client.get_file_text.return_value = ""
        client.get_open_issues.return_value = []

        result = get_recent_evidence()

        client.compare.assert_called_once_with(base="b" * 40, head="c" * 40)
        self.assertEqual(result["baseline_cursor"], "b" * 40)
        self.assertEqual(result["commits_since_baseline"], 0)

    @patch("app.server.MemoryRepository")
    def test_explicit_save_is_idempotent_and_project_scoped(self, repository_class):
        memory = MagicMock()
        memory.model_dump.return_value = {
            "memory_id": "memory-second-reentry-01",
            "project_id": "statewake-demo",
            "memory_type": "interpretation_rule",
            "content": "Experimental implementation alone does not establish approved scope without explicit confirmation.",
            "authority": "explicit_user",
            "active": True,
        }
        repository_class.return_value.save_explicit_interpretation_rule.return_value = memory
        client = TestClient(app)

        saved = client.post(
            "/api/reentry/memory",
            json={"project_id": "statewake-demo", "confirmed": True},
        )
        self.assertEqual(saved.status_code, 200)
        repository_class.return_value.save_explicit_interpretation_rule.assert_called_once_with(
            project_id="statewake-demo", confirmed=True
        )

        not_now = client.post(
            "/api/reentry/memory",
            json={"project_id": "statewake-demo", "confirmed": False},
        )
        self.assertEqual(not_now.status_code, 400)

        wrong_project = client.post(
            "/api/reentry/memory",
            json={"project_id": "other-project", "confirmed": True},
        )
        self.assertEqual(wrong_project.status_code, 403)


if __name__ == "__main__":
    unittest.main()
