from __future__ import annotations

from app.models.memory import MemoryType, ProjectMemory
from app.services.firestore_repository import FirestoreRepository


MEMORY_SUBCOLLECTION = "memory"
SECOND_REENTRY_MEMORY_ID = "memory-second-reentry-01"
SECOND_REENTRY_RULE = (
    "Experimental implementation alone does not establish approved scope "
    "without explicit confirmation."
)


class MemoryRepository:
    """Read-only repository for collaboration interpretation context."""

    def __init__(
        self,
        *,
        repository: FirestoreRepository | None = None,
    ) -> None:
        self.repository = repository or FirestoreRepository()

    def get_interpretation_rules(
        self,
        project_id: str,
    ) -> list[ProjectMemory]:
        memory_ref = (
            self.repository
            .project_ref(project_id)
            .collection(MEMORY_SUBCOLLECTION)
        )

        rules: list[ProjectMemory] = []
        for snapshot in memory_ref.stream():
            raw = snapshot.to_dict() or {}
            memory_type = raw.get(
                "memory_type",
                raw.get("type"),
            )

            if memory_type != MemoryType.INTERPRETATION_RULE:
                continue

            if raw.get("active", True) is False:
                continue

            content = raw.get("content", raw.get("rule"))
            if not isinstance(content, str) or not content.strip():
                continue

            rules.append(
                ProjectMemory(
                    memory_id=raw.get(
                        "memory_id",
                        snapshot.id,
                    ),
                    project_id=raw.get(
                        "project_id",
                        project_id,
                    ),
                    memory_type=MemoryType.INTERPRETATION_RULE,
                    content=content.strip(),
                    active=True,
                    authority=raw.get("authority", "system"),
                )
            )

        return rules

    def save_explicit_interpretation_rule(
        self,
        *,
        project_id: str,
        confirmed: bool,
    ) -> ProjectMemory:
        """Persist the one approved MVP rule after explicit confirmation."""

        if not confirmed:
            raise ValueError("Explicit confirmation is required to save memory.")

        memory = ProjectMemory(
            memory_id=SECOND_REENTRY_MEMORY_ID,
            project_id=project_id,
            memory_type=MemoryType.INTERPRETATION_RULE,
            content=SECOND_REENTRY_RULE,
            active=True,
            authority="explicit_user",
        )
        self.repository.project_ref(project_id).collection(
            MEMORY_SUBCOLLECTION
        ).document(memory.memory_id).set(memory.model_dump(mode="json"))
        return memory
