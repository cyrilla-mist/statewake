from __future__ import annotations

from google.cloud import firestore

from app.config import (
    FIRESTORE_PROJECTS_COLLECTION,
    GOOGLE_CLOUD_PROJECT,
)
from app.models.state import TrustedProjectState


class TrustedStateNotFoundError(RuntimeError):
    pass


class FirestoreRepository:
    """
    Durable STATEWAKE domain-state repository.

    This repository provides domain reads.

    Trusted Project State mutation must remain behind the
    bounded state-transition path rather than arbitrary callers.
    """

    def __init__(
        self,
        *,
        cloud_project: str = GOOGLE_CLOUD_PROJECT,
        projects_collection: str = FIRESTORE_PROJECTS_COLLECTION,
    ) -> None:
        self.client = firestore.Client(
            project=cloud_project
        )

        self.projects_collection = (
            projects_collection
        )

    def project_ref(
        self,
        project_id: str,
    ):
        return (
            self.client
            .collection(
                self.projects_collection
            )
            .document(
                project_id
            )
        )

    def get_trusted_state(
        self,
        project_id: str,
    ) -> TrustedProjectState:
        snapshot = (
            self.project_ref(
                project_id
            )
            .get()
        )

        if not snapshot.exists:
            raise TrustedStateNotFoundError(
                "Trusted Project State "
                f"does not exist: {project_id}"
            )

        raw = snapshot.to_dict()

        if raw is None:
            raise TrustedStateNotFoundError(
                "Trusted Project State "
                "returned no document data."
            )

        return TrustedProjectState(
            **raw
        )