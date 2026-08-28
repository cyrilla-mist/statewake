from google.cloud import firestore

from app.config import (
    DEMO_HERO_SESSION_ID,
    DEMO_PROJECT_ID,
    FIRESTORE_CHECKPOINTS_SUBCOLLECTION,
    FIRESTORE_PROJECTS_COLLECTION,
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
    GOOGLE_CLOUD_PROJECT,
    HERO_BASELINE_SHA,
)
from app.models.state import TrustedProjectState


SEED_STATE = TrustedProjectState(
    project_id=DEMO_PROJECT_ID,
    stateVersion=1,
    checkpoint_id="CP-01",
    evidence_cursor=HERO_BASELINE_SHA,
    goal=(
        "Ship a stable and convincing "
        "hackathon demo"
    ),
    direction="Feature A",
    priority="Technical depth",
    current_next_action=(
        "Finish Feature A integration"
    ),
)


def main() -> None:
    db = firestore.Client(
        project=GOOGLE_CLOUD_PROJECT
    )

    project_ref = (
        db.collection(
            FIRESTORE_PROJECTS_COLLECTION
        )
        .document(
            DEMO_PROJECT_ID
        )
    )

    project_ref.set(
        SEED_STATE.model_dump(
            mode="json"
        )
    )

    checkpoint_ref = (
        project_ref
        .collection(
            FIRESTORE_CHECKPOINTS_SUBCOLLECTION
        )
        .document("CP-01")
    )

    checkpoint_ref.set(
        {
            **SEED_STATE.model_dump(
                mode="json"
            ),
            "source_session_id": None,
            "bootstrap": True,
        }
    )

    # Reset any previous recovery state.
    (
        project_ref
        .collection(
            FIRESTORE_CHECKPOINTS_SUBCOLLECTION
        )
        .document("CP-02")
        .delete()
    )

    (
        project_ref
        .collection(
            FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION
        )
        .document(
            DEMO_HERO_SESSION_ID
        )
        .delete()
    )

    print(
        "STATEWAKE demo Trusted State seeded."
    )
    print("project_id = statewake-demo")
    print("stateVersion = 1")
    print("checkpoint = CP-01")
    print(
        f"evidence_cursor = "
        f"{HERO_BASELINE_SHA}"
    )


if __name__ == "__main__":
    main()