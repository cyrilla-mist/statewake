import unittest
from unittest.mock import MagicMock, patch

from scripts.reset_demo_state import (
    SECOND_REENTRY_MEMORY_ID,
    main,
)


class ResetDemoStateTest(unittest.TestCase):
    @patch("scripts.reset_demo_state.firestore.Client")
    def test_reset_restores_clean_baseline_and_removes_all_sessions(self, client_factory):
        client = client_factory.return_value
        project_ref = MagicMock(name="project_ref")
        checkpoints = MagicMock(name="checkpoints")
        sessions = MagicMock(name="sessions")
        session_a = MagicMock(name="completed_natural_session")
        session_a.reference = "reentry-session-01"
        session_b = MagicMock(name="hero_session")
        session_b.reference = "session-hero-01"
        sessions.stream.return_value = [session_a, session_b]
        memory = MagicMock(name="memory")
        memory_snapshot = MagicMock(name="second_reentry_memory")
        memory_snapshot.to_dict.return_value = {
            "memory_id": SECOND_REENTRY_MEMORY_ID,
            "active": True,
        }
        memory.stream.return_value = [memory_snapshot]
        project_ref.collection.side_effect = lambda name: (
            checkpoints
            if name == "checkpoints"
            else sessions
            if name == "reentrySessions"
            else memory
        )
        client.collection.return_value.document.return_value = project_ref
        batch = MagicMock(name="batch")
        client.batch.return_value = batch
        baseline_snapshot = MagicMock(exists=True)
        baseline_snapshot.to_dict.return_value = {
            "project_id": "statewake-demo",
            "stateVersion": 1,
            "checkpoint_id": "CP-01",
            "evidence_cursor": "ad23bfdca4001f5d7a70dc2a3d845ea6b6db780f",
            "goal": "Ship a stable and convincing hackathon demo",
            "direction": "Feature A",
            "priority": "Technical depth",
            "current_next_action": "Finish Feature A integration",
            "source_session_id": None,
            "bootstrap": True,
        }
        project_ref.get.return_value = baseline_snapshot
        checkpoints.document.return_value.get.side_effect = [
            baseline_snapshot,
            MagicMock(exists=False),
            MagicMock(exists=False),
        ]
        sessions.stream.side_effect = [
            [session_a, session_b],
            [],
        ]
        memory.stream.side_effect = [
            [memory_snapshot],
            [memory_snapshot],
        ]
        memory_snapshot.to_dict.side_effect = [
            {"memory_id": SECOND_REENTRY_MEMORY_ID, "active": True},
            {"memory_id": SECOND_REENTRY_MEMORY_ID, "active": False},
        ]
        with patch("scripts.reset_demo_state.GitHubClient") as github_factory:
            github_factory.return_value.get_branch_head_sha.return_value = "f" * 40

            main()

        self.assertEqual(batch.set.call_count, 2)
        self.assertEqual(batch.delete.call_count, 4)
        batch.update.assert_called_once_with(
            memory_snapshot.reference,
            {"active": False},
        )
        batch.commit.assert_called_once_with()

    @patch("scripts.reset_demo_state.firestore.Client")
    def test_reset_is_idempotent_when_no_sessions_remain(self, client_factory):
        client = client_factory.return_value
        project_ref = MagicMock(name="project_ref")
        checkpoints = MagicMock(name="checkpoints")
        sessions = MagicMock(name="sessions")
        sessions.stream.return_value = []
        project_ref.collection.side_effect = lambda name: (
            checkpoints
            if name == "checkpoints"
            else sessions
            if name == "reentrySessions"
            else MagicMock(name="memory")
        )
        client.collection.return_value.document.return_value = project_ref
        batch = MagicMock(name="batch")
        client.batch.return_value = batch
        baseline_snapshot = MagicMock(exists=True)
        baseline_snapshot.to_dict.return_value = {
            "project_id": "statewake-demo",
            "stateVersion": 1,
            "checkpoint_id": "CP-01",
            "evidence_cursor": "ad23bfdca4001f5d7a70dc2a3d845ea6b6db780f",
            "goal": "Ship a stable and convincing hackathon demo",
            "direction": "Feature A",
            "priority": "Technical depth",
            "current_next_action": "Finish Feature A integration",
            "source_session_id": None,
            "bootstrap": True,
        }
        project_ref.get.return_value = baseline_snapshot
        checkpoints.document.return_value.get.side_effect = [
            baseline_snapshot,
            MagicMock(exists=False),
            MagicMock(exists=False),
            baseline_snapshot,
            MagicMock(exists=False),
            MagicMock(exists=False),
        ]
        with patch("scripts.reset_demo_state.GitHubClient") as github_factory:
            github_factory.return_value.get_branch_head_sha.return_value = "f" * 40

            main()
            main()

        self.assertEqual(client.batch.call_count, 2)
        self.assertEqual(batch.set.call_count, 4)
        self.assertEqual(batch.delete.call_count, 4)
        self.assertEqual(batch.commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
