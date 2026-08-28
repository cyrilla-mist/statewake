from __future__ import annotations

from app.config import DEMO_PROJECT_ID
from app.services.memory_repository import MemoryRepository


def get_project_memory() -> dict:
    """Return read-only collaboration context for evidence interpretation."""

    repository = MemoryRepository()
    memories = repository.get_interpretation_rules(DEMO_PROJECT_ID)

    return {
        "status": "success",
        "source": "collaboration_memory",
        "project_id": DEMO_PROJECT_ID,
        "memory": [
            memory.model_dump(mode="json")
            for memory in memories
        ],
    }
