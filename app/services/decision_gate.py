from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.reentry import OverallValidity, ValidityResult
from app.models.state import TrustedProjectState
from app.tools.prepare_resume_state import prepare_resume_state


class DecisionGateAuthorizationError(ValueError):
    """Raised when an INVALID result lacks valid recovery authorization."""


def _state_value(
    state: TrustedProjectState | Mapping[str, Any],
    field: str,
) -> Any:
    if isinstance(state, TrustedProjectState):
        return getattr(state, field)
    return state.get(field)


class DecisionGateService:
    """Controlled bridge from validity assessment to authorized recovery."""

    def evaluate(
        self,
        validity: ValidityResult,
        trusted_state: TrustedProjectState | Mapping[str, Any],
        authorized_recovery_session: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if validity.overall_validity == OverallValidity.VALID:
            return {
                "status": "success",
                "decision": "aligned",
                "mutated": False,
                "message": "Trusted working state remains aligned.",
            }

        if validity.overall_validity == OverallValidity.AMBIGUOUS:
            return {
                "status": "success",
                "decision": "clarification_required",
                "mutated": False,
                "authorization_question": (
                    "Which direction should STATEWAKE continue with: "
                    "the trusted direction or a newly observed direction?"
                ),
            }

        if validity.overall_validity != OverallValidity.INVALID:
            raise ValueError(
                f"Unsupported validity result: {validity.overall_validity!r}"
            )

        self._validate_recovery_authorization(
            trusted_state=trusted_state,
            authorized_session=authorized_recovery_session,
        )

        assert authorized_recovery_session is not None
        result = prepare_resume_state(
            project_id=authorized_recovery_session["project_id"],
            session_id=authorized_recovery_session["session_id"],
            expected_state_version=(
                authorized_recovery_session["expected_state_version"]
            ),
            approved_resolution_id=(
                authorized_recovery_session["approved_resolution_id"]
            ),
        )

        return {
            "status": "success",
            "decision": "recovery_required",
            "mutated": True,
            "resume_state": result,
        }

    def commit_authorized_resolution(
        self,
        validity: ValidityResult,
        trusted_state: TrustedProjectState | Mapping[str, Any],
        authorized_recovery_session: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Resolve an AMBIGUOUS result after explicit human authorization.

        Normal evaluation of AMBIGUOUS remains clarification-only. This
        separate method is reachable only from the bounded authorization
        endpoint and still delegates the write exclusively to the writer.
        """

        if (
            validity.overall_validity != OverallValidity.AMBIGUOUS
            and authorized_recovery_session.get("status") != "COMPLETED"
        ):
            raise ValueError(
                "Authorized ambiguity resolution requires an AMBIGUOUS result."
            )

        self._validate_recovery_authorization(
            trusted_state=trusted_state,
            authorized_session=authorized_recovery_session,
            allow_completed=True,
        )

        result = prepare_resume_state(
            project_id=authorized_recovery_session["project_id"],
            session_id=authorized_recovery_session["session_id"],
            expected_state_version=(
                authorized_recovery_session["expected_state_version"]
            ),
            approved_resolution_id=(
                authorized_recovery_session["approved_resolution_id"]
            ),
        )

        return {
            "status": "success",
            "decision": "recovery_required",
            "mutated": result.get("status") == "COMMITTED",
            "resume_state": result,
        }

    def _validate_recovery_authorization(
        self,
        *,
        trusted_state: TrustedProjectState | Mapping[str, Any],
        authorized_session: Mapping[str, Any] | None,
        allow_completed: bool = False,
    ) -> None:
        if authorized_session is None:
            raise DecisionGateAuthorizationError(
                "INVALID validity requires an authorized recovery session."
            )

        required_fields = {
            "project_id",
            "session_id",
            "status",
            "expected_state_version",
            "approved_resolution_id",
            "allowed_resolution_ids",
        }

        missing = sorted(
            field
            for field in required_fields
            if field not in authorized_session
        )
        if missing:
            raise DecisionGateAuthorizationError(
                f"Recovery session is missing authorization fields: {missing}."
            )

        allowed_statuses = {"READY_TO_COMMIT"}
        if allow_completed:
            allowed_statuses.add("COMPLETED")
        if authorized_session["status"] not in allowed_statuses:
            raise DecisionGateAuthorizationError(
                "Recovery session is not in an authorized commit state."
            )

        project_id = _state_value(trusted_state, "project_id")
        state_version = _state_value(trusted_state, "stateVersion")

        if not project_id or authorized_session["project_id"] != project_id:
            raise DecisionGateAuthorizationError(
                "Recovery session project does not match Trusted State."
            )

        expected_version = authorized_session["expected_state_version"]
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            raise DecisionGateAuthorizationError(
                "Recovery session expected_state_version must be an integer."
            )

        if (
            authorized_session["status"] != "COMPLETED"
            and expected_version != state_version
        ):
            raise DecisionGateAuthorizationError(
                "Recovery session version does not match Trusted State."
            )

        resolution_id = authorized_session["approved_resolution_id"]
        allowed_resolution_ids = authorized_session["allowed_resolution_ids"]
        if (
            not isinstance(resolution_id, str)
            or not resolution_id
            or not isinstance(allowed_resolution_ids, list)
            or resolution_id not in allowed_resolution_ids
        ):
            raise DecisionGateAuthorizationError(
                "Approved recovery resolution is not authorized."
            )

        if (
            not isinstance(authorized_session["session_id"], str)
            or not authorized_session["session_id"]
        ):
            raise DecisionGateAuthorizationError(
                "Recovery session must have a valid session_id."
            )
