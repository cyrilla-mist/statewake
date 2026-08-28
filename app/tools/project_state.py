from __future__ import annotations

from app.config import DEMO_PROJECT_ID
from app.services.firestore_repository import (
    FirestoreRepository,
)


def get_project_state() -> dict:
    """
    Return the last trusted working state for the STATEWAKE project.

    The returned state is durable, previously committed project state.
    Current external evidence may challenge it, but must not silently
    overwrite it.
    """

    repository = FirestoreRepository()

    state = repository.get_trusted_state(
        DEMO_PROJECT_ID
    )

    return {
        "status": "success",
        "source": "firestore",
        "project_state": state.model_dump(
            mode="json"
        ),
    }