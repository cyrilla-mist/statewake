from datetime import datetime, timezone

from google.cloud import firestore

from app.config import (
    DEMO_HERO_CURRENT_SHA,
    DEMO_HERO_SESSION_ID,
    DEMO_PROJECT_ID,
    FIRESTORE_PROJECTS_COLLECTION,
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
    GOOGLE_CLOUD_PROJECT,
)


RESOLUTION_ID = "MOVE_FORWARD_WITH_B"


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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

    session_ref = (
        project_ref
        .collection(
            FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION
        )
        .document(
            DEMO_HERO_SESSION_ID
        )
    )

    session_ref.set(
        {
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

            "created_at":
                utc_now_iso(),
        }
    )

    print(
        "Hero Re-entry session seeded."
    )
    print(
        f"session = "
        f"{DEMO_HERO_SESSION_ID}"
    )
    print(
        "status = READY_TO_COMMIT"
    )
    print(
        "resolution = "
        f"{RESOLUTION_ID}"
    )


if __name__ == "__main__":
    main()