from __future__ import annotations

from typing import Any, Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from app.config import (
    ADK_SESSION_ID,
    DEMO_PROJECT_ID,
)
from app.models.reentry import ValidityResult
from app.services.decision_gate import (
    DecisionGateAuthorizationError,
    DecisionGateService,
)
from app.services.github_client import GitHubRateLimitError
from app.services.memory_repository import MemoryRepository
from app.services.reentry_session import (
    ReentrySessionAuthorizationError,
    ReentrySessionNotFoundError,
    ReentrySessionService,
)
from app.services.state_transition import StateTransitionError
from app.tools.github_evidence import get_recent_evidence
from app.tools.project_state import get_project_state
from app.workflows.reentry_flow import run_reentry_flow


class ResolutionRequest(BaseModel):
    """The only client-controlled fields accepted for recovery authorization."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    session_id: str
    expected_state_version: int
    approved_resolution_id: Literal["MOVE_FORWARD_WITH_B", "DEFER"]


class ReentryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = False


class MemorySaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    confirmed: bool


app = FastAPI(title="STATEWAKE API", version="0.8")
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "product": "STATEWAKE"}


@app.get("/api/status")
async def status() -> dict[str, str]:
    return {"status": "ok", "service": "STATEWAKE"}


@app.get("/api/project")
async def project() -> dict[str, Any]:
    return {
        "status": "success",
        "project_state": get_project_state()["project_state"],
    }


def _read_context() -> tuple[dict[str, Any], dict[str, Any]]:
    state = get_project_state()
    evidence = get_recent_evidence()
    return state["project_state"], {
        "repository": evidence.get("repository"),
        "current_cursor": evidence.get("current_cursor"),
        "baseline_cursor": evidence.get("baseline_cursor"),
        "commits_since_baseline": evidence.get("commits_since_baseline"),
        "evidence": evidence.get("evidence", []),
    }


def _read_authorization_context(
    trusted_state: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        session = ReentrySessionService().load(
            project_id=DEMO_PROJECT_ID,
            session_id=ADK_SESSION_ID,
        )
    except ReentrySessionNotFoundError:
        return None
    return ReentrySessionService.public_context(session)



def _response(
    result: dict[str, Any],
    context: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    trusted_state, evidence = context or _read_context()
    response = {
        "status": result["status"],
        "validity": result["validity"],
        "decision": {
            "type": result["decision"],
            "message": result["user_message"],
        },
        "trusted_state": trusted_state,
        "evidence": evidence,
        "applied_memory": result.get("applied_memory", []),
        "resume_state": result.get("resume_state"),
    }
    # Authorization is a current-session projection, not durable project
    # context. Only clarification results may resolve it from the active
    # session; aligned results must not inherit a completed Hero session.
    authorization = result.get("authorization")
    current_validity = result.get("validity") or {}
    if (
        authorization is None
        and current_validity.get("clarification_required") is True
    ):
        authorization = _read_authorization_context(trusted_state)
    response["authorization"] = authorization
    return response


def _committed_resume_projection(
    commit_result: dict[str, Any],
    committed_state: dict[str, Any],
) -> dict[str, Any]:
    """Expose the committed state used by the Resume screen.

    The writer returns commit metadata, while the state read used to authorize
    the transition is necessarily the pre-commit snapshot.  Build the UI
    projection only from a post-commit Trusted State read.
    """
    return {
        **commit_result,
        "state_version": committed_state["stateVersion"],
        "checkpoint_id": committed_state["checkpoint_id"],
        "direction": committed_state["direction"],
        "priority": committed_state["priority"],
        "do_first": committed_state["current_next_action"],
        "ignore_for_now": "Feature A integration",
    }


@app.post("/api/reentry")
async def reentry(
    request: ReentryRequest | None = None,
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    requested_dry_run = request.dry_run if request is not None else dry_run
    try:
        result = await run_reentry_flow(dry_run=requested_dry_run)
        trusted_state, evidence = _read_context()
        validity = ValidityResult.model_validate(result["validity"])
        if (
            not requested_dry_run
            and validity.overall_validity.value == "AMBIGUOUS"
            and result["decision"] == "clarification_required"
        ):
            session = ReentrySessionService().create_awaiting_clarification(
                project_id=DEMO_PROJECT_ID,
                session_id=ADK_SESSION_ID,
                expected_state_version=trusted_state["stateVersion"],
                validity=validity,
                evidence=evidence,
            )
            result["authorization"] = ReentrySessionService.public_context(session)
        return _response(result, context=(trusted_state, evidence))
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "remaining": exc.remaining, "reset": exc.reset},
        ) from exc
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/reentry/resolution")
async def resolve_reentry(request: ResolutionRequest) -> dict[str, Any]:
    if request.project_id != DEMO_PROJECT_ID:
        raise HTTPException(status_code=403, detail="Unknown project.")
    try:
        service = ReentrySessionService()
        session = service.load(
            project_id=request.project_id,
            session_id=request.session_id,
        )
        session = service.authorize(
            project_id=request.project_id,
            session_id=request.session_id,
            approved_resolution_id=request.approved_resolution_id,
            expected_state_version=request.expected_state_version,
        )
        trusted_state = get_project_state()["project_state"]
        validity = ValidityResult.model_validate(session["validity"])

        if session["status"] == "DEFERRED":
            result = {
                "status": "success",
                "validity": validity.model_dump(mode="json"),
                "decision": "deferred",
                "user_message": "Recovery deferred. Trusted State was not changed.",
            }
        else:
            authorized = {
                "project_id": request.project_id,
                "session_id": request.session_id,
                "status": session["status"],
                "expected_state_version": request.expected_state_version,
                "approved_resolution_id": request.approved_resolution_id,
                "allowed_resolution_ids": session.get("allowed_resolution_ids", []),
            }
            decision = DecisionGateService().commit_authorized_resolution(
                validity=validity,
                trusted_state=trusted_state,
                authorized_recovery_session=authorized,
            )
            committed_state = get_project_state()["project_state"]
            decision["resume_state"] = _committed_resume_projection(
                decision["resume_state"],
                committed_state,
            )
            result = {
                **decision,
                "validity": validity.model_dump(mode="json"),
                "user_message": (
                    "Authorized recovery was already committed."
                    if decision["resume_state"]["status"] == "ALREADY_COMMITTED"
                    else "Authorized recovery completed and Resume State was committed."
                ),
                "authorization": ReentrySessionService.public_context(session),
            }
        return _response(
            result,
            context=(
                get_project_state()["project_state"],
                {"evidence": [], "refresh": "skipped_after_session_transition"},
            ),
        )
    except DecisionGateAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ReentrySessionAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ReentrySessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "remaining": exc.remaining, "reset": exc.reset},
        ) from exc
    except StateTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/reentry/memory")
async def save_reentry_memory(request: MemorySaveRequest) -> dict[str, Any]:
    """Save only the fixed interpretation rule after explicit user consent."""

    if request.project_id != DEMO_PROJECT_ID:
        raise HTTPException(status_code=403, detail="Unknown project.")
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit confirmation is required to save memory.",
        )

    try:
        memory = MemoryRepository().save_explicit_interpretation_rule(
            project_id=request.project_id,
            confirmed=request.confirmed,
        )
        return {
            "status": "success",
            "memory": memory.model_dump(mode="json"),
        }
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
