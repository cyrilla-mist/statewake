from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from google.cloud import firestore

from app.config import (
    FIRESTORE_CHECKPOINTS_SUBCOLLECTION,
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
)
from app.services.firestore_repository import (
    FirestoreRepository,
)


# ============================================================
# ERRORS
# ============================================================

class StateTransitionError(RuntimeError):
    pass


class ProjectStateMissingError(
    StateTransitionError
):
    pass


class ReentrySessionMissingError(
    StateTransitionError
):
    pass


class InvalidSessionStateError(
    StateTransitionError
):
    pass


class InvalidResolutionError(
    StateTransitionError
):
    pass


class StaleStateVersionError(
    StateTransitionError
):
    pass


class InvalidMutationError(
    StateTransitionError
):
    pass


class CheckpointCollisionError(
    StateTransitionError
):
    pass


# ============================================================
# MUTATION POLICY
# ============================================================

ALLOWED_MUTATION_FIELDS = {
    "goal",
    "direction",
    "priority",
    "current_next_action",
    "evidence_cursor",
}


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class StateTransitionService:
    """
    The bounded STATEWAKE Trusted-State transition service.

    This is the only production service allowed to modify
    Trusted Project State.

    The caller does NOT supply replacement project state.
    It supplies only:
      - project identity
      - re-entry session identity
      - expected stateVersion
      - approved resolution identity

    Actual mutations must already be staged and authorized
    inside the Re-entry Session.
    """

    def __init__(
        self,
        repository: FirestoreRepository | None = None,
    ) -> None:
        self.repository = (
            repository
            or FirestoreRepository()
        )

        self.client = (
            self.repository.client
        )

    def session_ref(
        self,
        project_id: str,
        session_id: str,
    ):
        return (
            self.repository
            .project_ref(project_id)
            .collection(
                FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION
            )
            .document(session_id)
        )

    def checkpoint_ref(
        self,
        project_id: str,
        checkpoint_id: str,
    ):
        return (
            self.repository
            .project_ref(project_id)
            .collection(
                FIRESTORE_CHECKPOINTS_SUBCOLLECTION
            )
            .document(checkpoint_id)
        )

    def prepare_resume_state(
        self,
        *,
        project_id: str,
        session_id: str,
        expected_state_version: int,
        approved_resolution_id: str,
    ) -> dict:

        project_ref = (
            self.repository
            .project_ref(project_id)
        )

        session_ref = (
            self.session_ref(
                project_id,
                session_id,
            )
        )

        transaction = (
            self.client.transaction()
        )

        @firestore.transactional
        def commit_transition(
            transaction,
        ):
            # =================================================
            # READS FIRST
            # =================================================

            project_snapshot = (
                project_ref.get(
                    transaction=transaction
                )
            )

            session_snapshot = (
                session_ref.get(
                    transaction=transaction
                )
            )

            if not project_snapshot.exists:
                raise ProjectStateMissingError(
                    "Trusted Project State "
                    "does not exist."
                )

            if not session_snapshot.exists:
                raise ReentrySessionMissingError(
                    "Re-entry Session "
                    "does not exist."
                )

            project = (
                project_snapshot.to_dict()
            )

            session = (
                session_snapshot.to_dict()
            )

            if (
                project is None
                or session is None
            ):
                raise StateTransitionError(
                    "Firestore returned "
                    "empty document data."
                )

            # =================================================
            # IDENTITY
            # =================================================

            if (
                project.get("project_id")
                != project_id
            ):
                raise StateTransitionError(
                    "Project document identity "
                    "does not match request."
                )

            if (
                session.get("project_id")
                != project_id
            ):
                raise InvalidSessionStateError(
                    "Session belongs to "
                    "another project."
                )

            if (
                session.get("session_id")
                != session_id
            ):
                raise InvalidSessionStateError(
                    "Session identity "
                    "does not match request."
                )

            # =================================================
            # IDEMPOTENCY
            # =================================================

            if (
                session.get("status")
                == "COMPLETED"
            ):
                if (
                    session.get(
                        "expected_state_version"
                    )
                    != expected_state_version
                ):
                    raise InvalidSessionStateError(
                        "Repeated request changed "
                        "expected_state_version."
                    )

                if (
                    session.get(
                        "approved_resolution_id"
                    )
                    != approved_resolution_id
                ):
                    raise InvalidResolutionError(
                        "Repeated request changed "
                        "approved resolution."
                    )

                commit_result = (
                    session.get(
                        "commit_result"
                    )
                )

                if not commit_result:
                    raise InvalidSessionStateError(
                        "Completed session has "
                        "no commit_result."
                    )

                return {
                    "status":
                        "ALREADY_COMMITTED",

                    **commit_result,
                }

            # =================================================
            # SESSION STATE
            # =================================================

            if (
                session.get("status")
                != "READY_TO_COMMIT"
            ):
                raise InvalidSessionStateError(
                    "Session is not "
                    "READY_TO_COMMIT."
                )

            # =================================================
            # AUTHORIZATION
            # =================================================

            allowed_resolution_ids = (
                session.get(
                    "allowed_resolution_ids",
                    [],
                )
            )

            if (
                approved_resolution_id
                not in allowed_resolution_ids
            ):
                raise InvalidResolutionError(
                    "Resolution is not "
                    "authorized for session."
                )

            if (
                session.get(
                    "approved_resolution_id"
                )
                != approved_resolution_id
            ):
                raise InvalidResolutionError(
                    "Requested resolution "
                    "does not match the "
                    "staged approved resolution."
                )

            # =================================================
            # OPTIMISTIC VERSION CONTRACT
            # =================================================

            current_version = (
                project.get(
                    "stateVersion"
                )
            )

            if (
                current_version
                != expected_state_version
            ):
                raise StaleStateVersionError(
                    "State version mismatch: "
                    f"expected "
                    f"{expected_state_version}, "
                    f"current "
                    f"{current_version}."
                )

            if (
                session.get(
                    "expected_state_version"
                )
                != expected_state_version
            ):
                raise StaleStateVersionError(
                    "Session expected version "
                    "does not match request."
                )

            # =================================================
            # BOUNDED MUTATION
            # =================================================

            staged_mutations = (
                session.get(
                    "staged_mutations"
                )
            )

            if (
                not isinstance(
                    staged_mutations,
                    dict,
                )
                or not staged_mutations
            ):
                raise InvalidMutationError(
                    "Session has no staged "
                    "mutations."
                )

            mutation_fields = set(
                staged_mutations.keys()
            )

            prohibited_fields = (
                mutation_fields
                - ALLOWED_MUTATION_FIELDS
            )

            if prohibited_fields:
                raise InvalidMutationError(
                    "Prohibited Trusted-State "
                    "mutation fields: "
                    f"{sorted(prohibited_fields)}"
                )

            new_version = (
                current_version + 1
            )

            checkpoint_id = (
                f"CP-{new_version:02d}"
            )

            checkpoint_ref = (
                self.checkpoint_ref(
                    project_id,
                    checkpoint_id,
                )
            )

            # Still a READ.
            checkpoint_snapshot = (
                checkpoint_ref.get(
                    transaction=transaction
                )
            )

            if checkpoint_snapshot.exists:
                raise CheckpointCollisionError(
                    "Checkpoint already exists: "
                    f"{checkpoint_id}"
                )

            # =================================================
            # BUILD NEW STATE
            # =================================================

            new_project = deepcopy(
                project
            )

            for (
                field,
                value,
            ) in staged_mutations.items():
                new_project[field] = value

            new_project[
                "stateVersion"
            ] = new_version

            new_project[
                "checkpoint_id"
            ] = checkpoint_id

            checkpoint = {
                "checkpoint_id":
                    checkpoint_id,

                "project_id":
                    project_id,

                "stateVersion":
                    new_version,

                "evidence_cursor":
                    new_project[
                        "evidence_cursor"
                    ],

                "goal":
                    new_project["goal"],

                "direction":
                    new_project["direction"],

                "priority":
                    new_project["priority"],

                "current_next_action":
                    new_project[
                        "current_next_action"
                    ],

                "source_session_id":
                    session_id,

                "created_at":
                    utc_now_iso(),
            }

            commit_result = {
                "project_id":
                    project_id,

                "session_id":
                    session_id,

                "checkpoint_id":
                    checkpoint_id,

                "stateVersion":
                    new_version,

                "evidence_cursor":
                    new_project[
                        "evidence_cursor"
                    ],
            }

            # =================================================
            # WRITES — SAME TRANSACTION
            # =================================================

            transaction.set(
                project_ref,
                new_project,
            )

            transaction.create(
                checkpoint_ref,
                checkpoint,
            )

            transaction.update(
                session_ref,
                {
                    "status":
                        "COMPLETED",

                    "commit_result":
                        commit_result,

                    "completed_at":
                        utc_now_iso(),
                },
            )

            return {
                "status":
                    "COMMITTED",

                **commit_result,
            }

        return commit_transition(
            transaction
        )