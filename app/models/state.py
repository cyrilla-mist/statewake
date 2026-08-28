from pydantic import BaseModel


class TrustedProjectState(BaseModel):
    project_id: str

    stateVersion: int
    checkpoint_id: str
    evidence_cursor: str

    goal: str
    direction: str
    priority: str
    current_next_action: str