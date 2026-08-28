import unittest

from app.config import (
    DEMO_PROJECT_ID,
    HERO_BASELINE_SHA,
)
from app.services.firestore_repository import (
    FirestoreRepository,
)
from app.tools.project_state import (
    get_project_state,
)


class ProjectStateTest(
    unittest.TestCase
):
    def test_repository_reads_cp01(
        self,
    ):
        repository = (
            FirestoreRepository()
        )

        state = (
            repository
            .get_trusted_state(
                DEMO_PROJECT_ID
            )
        )

        self.assertEqual(
            state.project_id,
            "statewake-demo",
        )

        self.assertEqual(
            state.stateVersion,
            1,
        )

        self.assertEqual(
            state.checkpoint_id,
            "CP-01",
        )

        self.assertEqual(
            state.evidence_cursor,
            HERO_BASELINE_SHA,
        )

        self.assertEqual(
            state.direction,
            "Feature A",
        )

        self.assertEqual(
            state.priority,
            "Technical depth",
        )

        self.assertEqual(
            state.current_next_action,
            "Finish Feature A integration",
        )

    def test_agent_tool_contract(
        self,
    ):
        result = get_project_state()

        self.assertEqual(
            result["status"],
            "success",
        )

        self.assertEqual(
            result["source"],
            "firestore",
        )

        state = result[
            "project_state"
        ]

        self.assertEqual(
            state["stateVersion"],
            1,
        )

        self.assertEqual(
            state["checkpoint_id"],
            "CP-01",
        )

        self.assertEqual(
            state["evidence_cursor"],
            HERO_BASELINE_SHA,
        )

        self.assertEqual(
            state["direction"],
            "Feature A",
        )


if __name__ == "__main__":
    unittest.main()