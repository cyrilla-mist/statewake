"""Explicitly seed the v1.1 demo interpretation rule.

This is operator-run demo setup. The Agent never writes collaboration memory.
"""

from app.config import DEMO_PROJECT_ID
from app.services.firestore_repository import FirestoreRepository
from app.services.memory_repository import MEMORY_SUBCOLLECTION


MEMORY_ID = "memory-second-reentry-01"
RULE = (
    "Experimental implementation alone does not establish approved scope "
    "without explicit confirmation."
)


def main() -> None:
    repository = FirestoreRepository()
    memory_ref = (
        repository.project_ref(DEMO_PROJECT_ID)
        .collection(MEMORY_SUBCOLLECTION)
        .document(MEMORY_ID)
    )
    memory_ref.set(
        {
            "memory_id": MEMORY_ID,
            "project_id": DEMO_PROJECT_ID,
            "memory_type": "interpretation_rule",
            "content": RULE,
            "authority": "explicit_user",
            "active": True,
        }
    )
    print(f"Seeded explicit demo memory: {MEMORY_ID}")


if __name__ == "__main__":
    main()
