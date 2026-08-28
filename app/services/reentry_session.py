from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from app.config import (
    FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION,
)
from app.models.reentry import ValidityResult
from app.services.firestore_repository import FirestoreRepository


class ReentrySessionError(RuntimeError):
    pass


class ReentrySessionNotFoundError(ReentrySessionError):
    pass


class ReentrySessionAuthorizationError(ReentrySessionError):
    pass


ALLOWED_RESOLUTION_IDS = ["MOVE_FORWARD_WITH_B", "DEFER"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded_hero_options(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build the fixed MVP proposal from normalized external evidence."""

    evidence_items = evidence.get("evidence", [])
    feature_b_active = any(
        item.get("id") == "state:feature-b"
        and item.get("data", {}).get("state", {}).get("role")
        == "primary-demo-flow"
        for item in evidence_items
    )
    if not feature_b_active:
        raise ReentrySessionAuthorizationError(
            "The bounded Feature B recovery option is not supported by current evidence."
        )

    current_cursor = evidence.get("current_cursor")
    if not current_cursor:
        raise ReentrySessionAuthorizationError(
            "Current evidence cursor is required before recovery can be staged."
        )

    return {
        "MOVE_FORWARD_WITH_B": {
            "direction": "Feature B",
            "priority": "Demo clarity",
            "current_next_action": "Resolve Cloud Run deployment failure",
            "evidence_cursor": current_cursor,
        },
        "DEFER": {},
    }


class ReentrySessionService:
    """Owns interpretation/recovery session lifecycle, not Trusted State."""

    def __init__(self, repository: FirestoreRepository | None = None) -> None:
        self.repository = repository or FirestoreRepository()
        self.client = self.repository.client

    def session_ref(self, project_id: str, session_id: str):
        return (
            self.repository.project_ref(project_id)
            .collection(FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION)
            .document(session_id)
        )

    def create_awaiting_clarification(
        self,
        *,
        project_id: str,
        session_id: str,
        expected_state_version: int,
        validity: ValidityResult,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        options = bounded_hero_options(evidence)
        existing_snapshot = self.session_ref(project_id, session_id).get(timeout=15)
        if existing_snapshot.exists:
            existing = existing_snapshot.to_dict() or {}
            if existing.get("status") in {"READY_TO_COMMIT", "COMPLETED"}:
                return existing
        session = {
            "session_id": session_id,
            "project_id": project_id,
            "status": "AWAITING_CLARIFICATION",
            "expected_state_version": expected_state_version,
            "validity": validity.model_dump(mode="json"),
            "allowed_resolution_ids": ALLOWED_RESOLUTION_IDS,
            "bounded_options": options,
            "evidence_cursor": evidence["current_cursor"],
            "staged_mutations": None,
            "created_at": utc_now_iso(),
        }
        self.session_ref(project_id, session_id).set(session)
        return session

    def load(self, *, project_id: str, session_id: str) -> dict[str, Any]:
        snapshot = self.session_ref(project_id, session_id).get(timeout=15)
        if not snapshot.exists:
            raise ReentrySessionNotFoundError("Re-entry session was not found.")
        return snapshot.to_dict() or {}

    def authorize(
        self,
        *,
        project_id: str,
        session_id: str,
        approved_resolution_id: str,
        expected_state_version: int,
    ) -> dict[str, Any]:
        session_ref = self.session_ref(project_id, session_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def transition(transaction):
            snapshot = session_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise ReentrySessionNotFoundError(
                    "Re-entry session was not found."
                )
            session = snapshot.to_dict() or {}
            status = session.get("status")

            if status == "COMPLETED":
                if session.get("expected_state_version") != expected_state_version:
                    raise ReentrySessionAuthorizationError(
                        "Repeated request changed expected_state_version."
                    )
                if session.get("approved_resolution_id") != approved_resolution_id:
                    raise ReentrySessionAuthorizationError(
                        "Repeated request changed approved resolution."
                    )
                return session

            if status == "DEFERRED":
                raise ReentrySessionAuthorizationError(
                    "Re-entry session was deferred."
                )
            if status != "AWAITING_CLARIFICATION":
                raise ReentrySessionAuthorizationError(
                    "Re-entry session is not awaiting clarification."
                )
            if session.get("expected_state_version") != expected_state_version:
                raise ReentrySessionAuthorizationError(
                    "Session expected_state_version does not match request."
                )
            allowed = session.get("allowed_resolution_ids", [])
            if approved_resolution_id not in allowed:
                raise ReentrySessionAuthorizationError(
                    "Resolution is not authorized for this session."
                )

            bounded_options = session.get("bounded_options", {})
            staged = bounded_options.get(approved_resolution_id)
            if approved_resolution_id == "DEFER":
                transaction.update(
                    session_ref,
                    {
                        "status": "DEFERRED",
                        "approved_resolution_id": "DEFER",
                        "completed_at": utc_now_iso(),
                    },
                )
                session["status"] = "DEFERRED"
                return session

            if not isinstance(staged, dict) or not staged:
                raise ReentrySessionAuthorizationError(
                    "No bounded recovery proposal exists for this resolution."
                )

            transaction.update(
                session_ref,
                {
                    "status": "READY_TO_COMMIT",
                    "approved_resolution_id": approved_resolution_id,
                    "staged_mutations": staged,
                    "authorized_at": utc_now_iso(),
                },
            )
            session.update(
                {
                    "status": "READY_TO_COMMIT",
                    "approved_resolution_id": approved_resolution_id,
                    "staged_mutations": staged,
                }
            )
            return session

        return transition(transaction)

    @staticmethod
    def public_context(session: dict[str, Any]) -> dict[str, Any]:
        return {
            "project_id": session.get("project_id"),
            "session_id": session.get("session_id"),
            "expected_state_version": session.get("expected_state_version"),
            "question": (
                "Which direction should STATEWAKE continue with: "
                "the trusted direction or a newly observed direction?"
            ),
            "allowed_resolution_ids": [
                resolution_id
                for resolution_id in session.get("allowed_resolution_ids", [])
                if resolution_id in ALLOWED_RESOLUTION_IDS
            ],
        }
