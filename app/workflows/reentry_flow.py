from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.main import run_user_return
from app.models.reentry import ValidityResult
from app.services.decision_gate import (
    DecisionGateAuthorizationError,
    DecisionGateService,
)
from app.tools.project_state import get_project_state


DRY_RUN_MESSAGE = "Dry run completed. No Trusted State mutation performed."


async def run_reentry_flow(
    authorized_recovery_session: Mapping[str, Any] | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the first production STATEWAKE User Return workflow."""

    agent_result = await run_user_return()
    validity = ValidityResult.model_validate(agent_result["validity"])

    state_result = get_project_state()
    trusted_state = state_result["project_state"]

    gate = DecisionGateService()

    if dry_run:
        try:
            # Never pass recovery authorization in dry-run mode. This still
            # executes the Decision Gate while making writer invocation
            # impossible on the INVALID path.
            decision_result = gate.evaluate(
                validity=validity,
                trusted_state=trusted_state,
                authorized_recovery_session=None,
            )
        except DecisionGateAuthorizationError:
            decision_result = {
                "status": "success",
                "decision": "recovery_required",
                "mutated": False,
            }
    else:
        if (
            authorized_recovery_session is not None
            and (
                validity.overall_validity.value == "AMBIGUOUS"
                or authorized_recovery_session.get("status") == "COMPLETED"
            )
        ):
            decision_result = gate.commit_authorized_resolution(
                validity=validity,
                trusted_state=trusted_state,
                authorized_recovery_session=authorized_recovery_session,
            )
        else:
            decision_result = gate.evaluate(
                validity=validity,
                trusted_state=trusted_state,
                authorized_recovery_session=authorized_recovery_session,
            )

    response: dict[str, Any] = {
        "status": decision_result["status"],
        "validity": validity.model_dump(mode="json"),
        "decision": decision_result["decision"],
        "user_message": (
            DRY_RUN_MESSAGE
            if dry_run
            else _user_message(decision_result)
        ),
        "applied_memory": agent_result.get("applied_memory", []),
    }

    if "resume_state" in decision_result:
        response["resume_state"] = decision_result["resume_state"]

    return response


def _user_message(decision_result: Mapping[str, Any]) -> str:
    if decision_result["decision"] == "clarification_required":
        return decision_result["authorization_question"]

    if decision_result["decision"] == "recovery_required":
        if decision_result.get("mutated"):
            return "Authorized recovery completed and Resume State was committed."
        return "Authorized recovery was already committed."

    return decision_result["message"]
