from __future__ import annotations

from app.config import DEMO_PROJECT_ID
from app.services.state_transition import (
    StateTransitionService,
)


def prepare_resume_state(
    project_id: str,
    session_id: str,
    expected_state_version: int,
    approved_resolution_id: str,
) -> dict:
    """
    Commit an authorized STATEWAKE Resume State.

    This is the ONLY agent-visible tool that may modify
    Trusted Project State.

    The caller cannot provide arbitrary replacement state.
    All mutations must already be staged inside the
    authorized Re-entry Session.
    """

    if project_id != DEMO_PROJECT_ID:
        raise ValueError(
            "The hackathon MVP is configured "
            "for exactly one project."
        )

    service = (
        StateTransitionService()
    )

    return service.prepare_resume_state(
        project_id=project_id,
        session_id=session_id,
        expected_state_version=(
            expected_state_version
        ),
        approved_resolution_id=(
            approved_resolution_id
        ),
    )