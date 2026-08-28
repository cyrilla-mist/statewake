from enum import StrEnum

from pydantic import BaseModel


class MemoryType(StrEnum):
    """Supported collaboration-memory categories for the MVP."""

    INTERPRETATION_RULE = "interpretation_rule"


class ProjectMemory(BaseModel):
    """Read-only collaboration context, never Trusted Project State."""

    memory_id: str
    project_id: str
    memory_type: MemoryType
    content: str
    active: bool = True
    authority: str = "system"
