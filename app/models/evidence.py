from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EvidenceStrength(StrEnum):
    WEAK = "weak"
    CORROBORATING = "corroborating"
    DIRECT = "direct"


class EvidenceKind(StrEnum):
    COMMIT = "commit"
    FILE_DIFF = "file_diff"
    CODE_STATE = "code_state"
    DEPLOYMENT_STATE = "deployment_state"
    PRESENTATION_STATE = "presentation_state"
    DOCUMENTATION = "documentation"
    OPEN_ISSUE = "open_issue"


class Evidence(BaseModel):
    id: str
    source: str = "github"
    kind: EvidenceKind
    strength: EvidenceStrength

    summary: str | None = None
    data: dict[str, Any] | None = None