"""Reset the known STATEWAKE Hero fixture for demos and recordings.

This is internal hackathon/demo bootstrap infrastructure. It is not an
Agent-visible tool and is not exposed through the public API.
"""

from google.cloud import firestore

from app.config import (
    DEMO_PROJECT_ID,
    FIRESTORE_CHECKPOINTS_SUBCOLLECTION,
    FIRESTORE_PROJECTS_COLLECTION,
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
    GOOGLE_CLOUD_PROJECT,
    HERO_BASELINE_SHA,
)
from app.services.github_client import GitHubClient


RESET_TARGET_PROJECT_ID = "statewake-demo"
SECOND_REENTRY_MEMORY_ID = "memory-second-reentry-01"
SECOND_REENTRY_MEMORY_CONTENT = (
    "Experimental implementation alone does not establish approved scope "
    "without explicit confirmation."
)


def _assert_baseline(snapshot, expected: dict, label: str) -> None:
    if not snapshot.exists:
        raise RuntimeError(f"{label} is missing after demo reset.")
    actual = snapshot.to_dict() or {}
    for key, value in expected.items():
        if actual.get(key) != value:
            raise RuntimeError(
                f"{label} mismatch for {key}: "
                f"expected {value!r}, got {actual.get(key)!r}."
            )


def _assert_deleted(snapshot, label: str) -> None:
    if snapshot.exists:
        raise RuntimeError(f"{label} still exists after demo reset.")


def main() -> None:
    if DEMO_PROJECT_ID != RESET_TARGET_PROJECT_ID:
        raise RuntimeError(
            "Demo reset is restricted to the statewake-demo project."
        )

    db = firestore.Client(project=GOOGLE_CLOUD_PROJECT)
    project_ref = db.collection(FIRESTORE_PROJECTS_COLLECTION).document(DEMO_PROJECT_ID)
    checkpoint_ref = project_ref.collection(FIRESTORE_CHECKPOINTS_SUBCOLLECTION)
    sessions_ref = project_ref.collection(FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION)
    memory_ref = project_ref.collection("memory")

    initial_state = {
        "project_id": DEMO_PROJECT_ID,
        "stateVersion": 1,
        "checkpoint_id": "CP-01",
        "evidence_cursor": HERO_BASELINE_SHA,
        "goal": "Ship a stable and convincing hackathon demo",
        "direction": "Feature A",
        "priority": "Technical depth",
        "current_next_action": "Finish Feature A integration",
    }
    batch = db.batch()
    batch.set(project_ref, initial_state)
    batch.set(
        checkpoint_ref.document("CP-01"),
        {**initial_state, "source_session_id": None, "bootstrap": True},
    )
    batch.delete(checkpoint_ref.document("CP-02"))
    batch.delete(checkpoint_ref.document("CP-03"))
    # The demo has used more than one durable session identity over time.
    # Delete every session in this isolated demo project so a completed
    # natural session cannot survive beside a reset CP-01 state.
    for session_snapshot in sessions_ref.stream():
        batch.delete(session_snapshot.reference)

    # Isolate the explicit second-reentry interpretation rule during the
    # first Hero run. This is not a production memory transition.
    for memory_snapshot in memory_ref.stream():
        raw = memory_snapshot.to_dict() or {}
        if (
            raw.get("memory_id") == SECOND_REENTRY_MEMORY_ID
            or raw.get("content") == SECOND_REENTRY_MEMORY_CONTENT
        ):
            batch.update(memory_snapshot.reference, {"active": False})

    batch.commit()

    _assert_baseline(project_ref.get(), initial_state, "Trusted State")
    checkpoint_snapshot = checkpoint_ref.document("CP-01").get()
    _assert_baseline(checkpoint_snapshot, initial_state, "CP-01")
    checkpoint_data = checkpoint_snapshot.to_dict() or {}
    if checkpoint_data.get("source_session_id") is not None:
        raise RuntimeError("CP-01 source_session_id must remain None.")
    if checkpoint_data.get("bootstrap") is not True:
        raise RuntimeError("CP-01 bootstrap marker is missing.")
    _assert_deleted(checkpoint_ref.document("CP-02").get(), "CP-02")
    _assert_deleted(checkpoint_ref.document("CP-03").get(), "CP-03")
    if list(sessions_ref.stream()):
        raise RuntimeError("A demo Re-entry session survived reset.")

    memory_active = False
    for memory_snapshot in memory_ref.stream():
        raw = memory_snapshot.to_dict() or {}
        if raw.get("memory_id") == SECOND_REENTRY_MEMORY_ID:
            memory_active = raw.get("active", True) is True
    if memory_active:
        raise RuntimeError("Second-reentry memory remains active.")

    # Post-Hero correctness item: get_recent_evidence currently compares from
    # the fixed HERO_BASELINE_SHA rather than the Trusted State cursor. Keep
    # that behavior unchanged in this reset task; address it separately.
    current_head = GitHubClient().get_branch_head_sha()
    if current_head == HERO_BASELINE_SHA:
        raise RuntimeError(
            "GitHub reality is not drifted from the Hero baseline."
        )

    print("STATEWAKE HERO DEMO RESET")
    print()
    print("Trusted checkpoint: CP-01")
    print("State version: 1")
    print("Direction: Feature A")
    print("Priority: Technical depth")
    print("Next action: Finish Feature A integration")
    print(f"Evidence cursor: {HERO_BASELINE_SHA}")
    print("Second-reentry memory active: NO")
    print(f"Current GitHub HEAD: {current_head}")
    print("GitHub changed since baseline: YES")
    print()
    print("STATUS: READY")


if __name__ == "__main__":
    main()
