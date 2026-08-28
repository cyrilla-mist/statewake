from __future__ import annotations

from app.models.evidence import (
    Evidence,
    EvidenceKind,
    EvidenceStrength,
)


class EvidenceNormalizer:
    """
    Convert raw GitHub observations into STATEWAKE Evidence objects.

    Evidence strength describes provenance quality.
    It does NOT determine materiality.
    """

    def normalize(
        self,
        *,
        compare_data: dict,
        head_sha: str,
        route: dict,
        feature_a: dict,
        feature_b: dict,
        deployment: dict,
        presentation: dict,
        readme: str,
        open_issues: list[dict],
    ) -> list[Evidence]:

        evidence: list[Evidence] = []

        # ----------------------------------------------------
        # COMMIT MESSAGES
        # Weak evidence: useful context, never sufficient truth.
        # ----------------------------------------------------

        for commit in compare_data.get(
            "commits",
            [],
        ):
            sha = commit["sha"]

            message = (
                commit["commit"]["message"]
                .splitlines()[0]
            )

            evidence.append(
                Evidence(
                    id=f"commit:{sha}",
                    kind=EvidenceKind.COMMIT,
                    strength=EvidenceStrength.WEAK,
                    summary=message,
                    data={
                        "sha": sha,
                        "url": commit.get(
                            "html_url"
                        ),
                    },
                )
            )

        # ----------------------------------------------------
        # ACTUAL FILE DIFF
        # Direct evidence.
        # ----------------------------------------------------

        for file_data in compare_data.get(
            "files",
            [],
        ):
            path = file_data[
                "filename"
            ]

            evidence.append(
                Evidence(
                    id=f"file-diff:{path}",
                    kind=EvidenceKind.FILE_DIFF,
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        f"{path} changed since "
                        "the trusted evidence cursor."
                    ),
                    data={
                        "path": path,
                        "status": file_data.get(
                            "status"
                        ),
                        "additions": file_data.get(
                            "additions"
                        ),
                        "deletions": file_data.get(
                            "deletions"
                        ),
                        "changes": file_data.get(
                            "changes"
                        ),
                        "patch": file_data.get(
                            "patch"
                        ),
                    },
                )
            )

        # ----------------------------------------------------
        # CURRENT PROJECT REALITY
        # ----------------------------------------------------

        evidence.extend(
            [
                Evidence(
                    id="state:active-route",
                    kind=EvidenceKind.CODE_STATE,
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        "Current /demo route "
                        f"resolves to "
                        f"{route['activeFeature']}."
                    ),
                    data={
                        "ref": head_sha,
                        "path": "app/route.json",
                        "state": route,
                    },
                ),
                Evidence(
                    id="state:feature-a",
                    kind=EvidenceKind.CODE_STATE,
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        "Current Feature A state."
                    ),
                    data={
                        "ref": head_sha,
                        "path": "app/feature-a.json",
                        "state": feature_a,
                    },
                ),
                Evidence(
                    id="state:feature-b",
                    kind=EvidenceKind.CODE_STATE,
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        "Current Feature B state."
                    ),
                    data={
                        "ref": head_sha,
                        "path": "app/feature-b.json",
                        "state": feature_b,
                    },
                ),
                Evidence(
                    id="state:deployment",
                    kind=EvidenceKind.DEPLOYMENT_STATE,
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        "Current Cloud Run "
                        "deployment state."
                    ),
                    data={
                        "ref": head_sha,
                        "path": (
                            "deployment/status.json"
                        ),
                        "state": deployment,
                    },
                ),
                Evidence(
                    id="state:presentation",
                    kind=(
                        EvidenceKind
                        .PRESENTATION_STATE
                    ),
                    strength=EvidenceStrength.DIRECT,
                    summary=(
                        "Current presentation-only "
                        "change state."
                    ),
                    data={
                        "ref": head_sha,
                        "path": (
                            "app/presentation.json"
                        ),
                        "state": presentation,
                    },
                ),
            ]
        )

        # ----------------------------------------------------
        # DOCUMENTATION
        # Corroborating, never authority.
        # ----------------------------------------------------

        evidence.append(
            Evidence(
                id="docs:readme",
                kind=EvidenceKind.DOCUMENTATION,
                strength=(
                    EvidenceStrength
                    .CORROBORATING
                ),
                summary=(
                    "README describes the "
                    "current demo flow."
                ),
                data={
                    "ref": head_sha,
                    "path": "README.md",
                    "content": readme,
                },
            )
        )

        # ----------------------------------------------------
        # OPEN ISSUES
        # Corroborating: open issue != automatic blocker.
        # ----------------------------------------------------

        for issue in open_issues:
            number = issue["number"]

            evidence.append(
                Evidence(
                    id=f"issue:{number}",
                    kind=EvidenceKind.OPEN_ISSUE,
                    strength=(
                        EvidenceStrength
                        .CORROBORATING
                    ),
                    summary=issue.get(
                        "title"
                    ),
                    data={
                        "issue_number": number,
                        "state": issue.get(
                            "state"
                        ),
                        "title": issue.get(
                            "title"
                        ),
                        "body": issue.get(
                            "body"
                        ),
                        "url": issue.get(
                            "html_url"
                        ),
                    },
                )
            )

        return evidence