import unittest
from copy import deepcopy

from google.cloud import firestore

from app.config import (
    DEMO_HERO_CURRENT_SHA,
    DEMO_HERO_SESSION_ID,
    DEMO_PROJECT_ID,
    FIRESTORE_CHECKPOINTS_SUBCOLLECTION,
    FIRESTORE_PROJECTS_COLLECTION,
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
    GOOGLE_CLOUD_PROJECT,
    HERO_BASELINE_SHA,
)
from app.services.state_transition import (
    CheckpointCollisionError,
    InvalidMutationError,
    InvalidResolutionError,
    StaleStateVersionError,
)
from app.tools.prepare_resume_state import (
    prepare_resume_state,
)


RESOLUTION_ID = "MOVE_FORWARD_WITH_B"


BASELINE_PROJECT = {
    "project_id":
        DEMO_PROJECT_ID,

    "stateVersion":
        1,

    "checkpoint_id":
        "CP-01",

    "evidence_cursor":
        HERO_BASELINE_SHA,

    "goal":
        (
            "Ship a stable and convincing "
            "hackathon demo"
        ),

    "direction":
        "Feature A",

    "priority":
        "Technical depth",

    "current_next_action":
        "Finish Feature A integration",
}


BASELINE_CP01 = {
    **deepcopy(BASELINE_PROJECT),
    "source_session_id": None,
    "bootstrap": True,
}


READY_SESSION = {
    "session_id":
        DEMO_HERO_SESSION_ID,

    "project_id":
        DEMO_PROJECT_ID,

    "status":
        "READY_TO_COMMIT",

    "expected_state_version":
        1,

    "approved_resolution_id":
        RESOLUTION_ID,

    "allowed_resolution_ids": [
        RESOLUTION_ID,
        "KEEP_DIRECTION_A",
    ],

    "staged_mutations": {
        "direction":
            "Feature B",

        "priority":
            "Demo clarity",

        "current_next_action":
            (
                "Resolve Cloud Run "
                "deployment failure"
            ),

        "evidence_cursor":
            DEMO_HERO_CURRENT_SHA,
    },

    "commit_result":
        None,
}


class PrepareResumeStateTest(
    unittest.TestCase
):
    def setUp(self):
        self.db = firestore.Client(
            project=GOOGLE_CLOUD_PROJECT
        )

        self.project_ref = (
            self.db.collection(
                FIRESTORE_PROJECTS_COLLECTION
            )
            .document(
                DEMO_PROJECT_ID
            )
        )

        self.cp01_ref = (
            self.project_ref
            .collection(
                FIRESTORE_CHECKPOINTS_SUBCOLLECTION
            )
            .document("CP-01")
        )

        self.cp02_ref = (
            self.project_ref
            .collection(
                FIRESTORE_CHECKPOINTS_SUBCOLLECTION
            )
            .document("CP-02")
        )

        self.session_ref = (
            self.project_ref
            .collection(
                FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION
            )
            .document(
                DEMO_HERO_SESSION_ID
            )
        )

        self.reset_fixture()

    def tearDown(self):
        self.reset_fixture()

    def reset_fixture(self):
        self.project_ref.set(
            deepcopy(BASELINE_PROJECT)
        )

        self.cp01_ref.set(
            deepcopy(BASELINE_CP01)
        )

        self.cp02_ref.delete()

        self.session_ref.set(
            deepcopy(READY_SESSION)
        )

    def read_fixture(self):
        project = (
            self.project_ref
            .get()
            .to_dict()
        )

        session = (
            self.session_ref
            .get()
            .to_dict()
        )

        cp02_snapshot = (
            self.cp02_ref.get()
        )

        cp02 = (
            cp02_snapshot.to_dict()
            if cp02_snapshot.exists
            else None
        )

        return {
            "project": project,
            "session": session,
            "cp02": cp02,
        }

    # ========================================================
    # SUCCESS
    # ========================================================

    def test_successful_commit(
        self,
    ):
        result = prepare_resume_state(
            project_id=DEMO_PROJECT_ID,
            session_id=DEMO_HERO_SESSION_ID,
            expected_state_version=1,
            approved_resolution_id=RESOLUTION_ID,
        )

        state = self.read_fixture()

        self.assertEqual(
            result["status"],
            "COMMITTED",
        )

        self.assertEqual(
            state["project"][
                "stateVersion"
            ],
            2,
        )

        self.assertEqual(
            state["project"][
                "checkpoint_id"
            ],
            "CP-02",
        )

        self.assertEqual(
            state["project"][
                "direction"
            ],
            "Feature B",
        )

        self.assertEqual(
            state["project"][
                "priority"
            ],
            "Demo clarity",
        )

        self.assertEqual(
            state["project"][
                "current_next_action"
            ],
            (
                "Resolve Cloud Run "
                "deployment failure"
            ),
        )

        self.assertEqual(
            state["project"][
                "evidence_cursor"
            ],
            DEMO_HERO_CURRENT_SHA,
        )

        self.assertIsNotNone(
            state["cp02"]
        )

        self.assertEqual(
            state["cp02"][
                "source_session_id"
            ],
            DEMO_HERO_SESSION_ID,
        )

        self.assertEqual(
            state["session"]["status"],
            "COMPLETED",
        )

    # ========================================================
    # IDEMPOTENCY
    # ========================================================

    def test_second_resume_is_idempotent(
        self,
    ):
        first = prepare_resume_state(
            project_id=DEMO_PROJECT_ID,
            session_id=DEMO_HERO_SESSION_ID,
            expected_state_version=1,
            approved_resolution_id=RESOLUTION_ID,
        )

        before = self.read_fixture()

        second = prepare_resume_state(
            project_id=DEMO_PROJECT_ID,
            session_id=DEMO_HERO_SESSION_ID,
            expected_state_version=1,
            approved_resolution_id=RESOLUTION_ID,
        )

        after = self.read_fixture()

        self.assertEqual(
            first["checkpoint_id"],
            "CP-02",
        )

        self.assertEqual(
            second["status"],
            "ALREADY_COMMITTED",
        )

        self.assertEqual(
            after["project"][
                "stateVersion"
            ],
            2,
        )

        self.assertEqual(
            before["cp02"],
            after["cp02"],
        )

    # ========================================================
    # STALE VERSION
    # ========================================================

    def test_stale_version_is_rejected(
        self,
    ):
        self.project_ref.update(
            {
                "stateVersion": 2,
            }
        )

        before = self.read_fixture()

        with self.assertRaises(
            StaleStateVersionError
        ):
            prepare_resume_state(
                project_id=DEMO_PROJECT_ID,
                session_id=DEMO_HERO_SESSION_ID,
                expected_state_version=1,
                approved_resolution_id=RESOLUTION_ID,
            )

        after = self.read_fixture()

        self.assertEqual(
            before,
            after,
        )

        self.assertIsNone(
            after["cp02"]
        )

    # ========================================================
    # INVALID RESOLUTION
    # ========================================================

    def test_invalid_resolution_rolls_back(
        self,
    ):
        before = self.read_fixture()

        with self.assertRaises(
            InvalidResolutionError
        ):
            prepare_resume_state(
                project_id=DEMO_PROJECT_ID,
                session_id=DEMO_HERO_SESSION_ID,
                expected_state_version=1,
                approved_resolution_id=(
                    "UNAUTHORIZED_DIRECTION_C"
                ),
            )

        after = self.read_fixture()

        self.assertEqual(
            before,
            after,
        )

    # ========================================================
    # IMMUTABLE CHECKPOINT
    # ========================================================

    def test_checkpoint_collision_rolls_back(
        self,
    ):
        sentinel = {
            "checkpoint_id":
                "CP-02",

            "sentinel":
                "DO_NOT_OVERWRITE",
        }

        self.cp02_ref.set(
            deepcopy(sentinel)
        )

        before = self.read_fixture()

        with self.assertRaises(
            CheckpointCollisionError
        ):
            prepare_resume_state(
                project_id=DEMO_PROJECT_ID,
                session_id=DEMO_HERO_SESSION_ID,
                expected_state_version=1,
                approved_resolution_id=RESOLUTION_ID,
            )

        after = self.read_fixture()

        self.assertEqual(
            before,
            after,
        )

        self.assertEqual(
            after["cp02"],
            sentinel,
        )

    # ========================================================
    # PROHIBITED MUTATION
    # ========================================================

    def test_prohibited_mutation_rolls_back(
        self,
    ):
        bad_session = deepcopy(
            READY_SESSION
        )

        bad_session[
            "staged_mutations"
        ][
            "checkpoint_id"
        ] = "EVIL-CP"

        self.session_ref.set(
            bad_session
        )

        before = self.read_fixture()

        with self.assertRaises(
            InvalidMutationError
        ):
            prepare_resume_state(
                project_id=DEMO_PROJECT_ID,
                session_id=DEMO_HERO_SESSION_ID,
                expected_state_version=1,
                approved_resolution_id=RESOLUTION_ID,
            )

        after = self.read_fixture()

        self.assertEqual(
            before,
            after,
        )


if __name__ == "__main__":
    unittest.main()