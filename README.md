# STATEWAKE

### Come back without starting over.

STATEWAKE is an interrupted-work recovery agent that verifies whether the
project state you trusted when you left is still safe to continue from.

> Most agents remember the past. STATEWAKE checks whether the past is still
> safe to continue from.

> The problem isn't forgetting. It's continuing from something that stopped
> being true.

## Live demo

- [STATEWAKE](https://statewake-73198201224.us-central1.run.app)
- [Demo Evidence Repository](https://github.com/cyrilla-mist/statewake-demo-project)

`statewake-demo-project` is not the STATEWAKE source repository. It is a
small public project used as live external project evidence during the demo.

## What STATEWAKE does

STATEWAKE reads a protected Trusted Working State, gathers current supporting
evidence, and assesses whether the previous continuation point still holds.
It validates before it recovers.

The epistemic boundary is explicit:

- Evidence is observed.
- Findings are inferred.
- Trusted State is committed.

## VALID, INVALID, AMBIGUOUS

- **VALID** — the trusted direction and next action remain aligned. The state
  is preserved and no new checkpoint is created.
- **INVALID** — the relevant invalidation is resolved and no consequential
  human-authority question remains.
- **AMBIGUOUS** — a protected-state conflict requires human authorization
  before a safe continuation state can be established. An invalid next action
  can coexist with an AMBIGUOUS overall result.

## Validate before Recover

The agent prioritizes Trusted Working State, explicit Human Authorization,
Collaboration Memory interpretation rules, and external evidence. Memory
cannot override state, create goals, authorize recovery, or write Firestore.
GitHub evidence supports interpretation but does not imply approval.

The Decision Gate is the controlled boundary for consequential choices.
`prepare_resume_state` is the only Trusted State writer and commits the new
checkpoint atomically with version checks and idempotency.

## Resume State

Authorized recovery produces a committed Resume State. The demo's CP-02 is:

- Direction: Feature B
- Priority: Demo clarity
- Do First: Resolve Cloud Run deployment failure
- Ignore for Now: Feature A integration

The evidence cursor advances with the committed state, so later re-entry starts
from the current trusted observation boundary rather than replaying the Hero
baseline.

## Collaboration Memory

Collaboration Memory is read-only interpretation context during assessment.
The demo stores this explicit-user interpretation rule:

> Experimental implementation alone does not establish approved scope without
> explicit confirmation.

It cannot mutate Trusted State or authorize a direction change.

## Demo flow

1. First Re-entry observes the Hero project after it moved away from Feature A:

   ```text
   OVERALL_VALIDITY: AMBIGUOUS
   PREVIOUS_NEXT_ACTION_VALID: NO
   DIRECTION_CONFLICT: YES
   CLARIFICATION_REQUIRED: YES
   ```

2. The user authorizes Move forward with Feature B. The Decision Gate delegates
   to `prepare_resume_state`, which commits CP-02.
3. A later Re-entry sees experimental Feature C evidence. With the saved rule,
   it remains aligned with CP-02:

   ```text
   OVERALL_VALIDITY: VALID
   PREVIOUS_NEXT_ACTION_VALID: YES
   DIRECTION_CONFLICT: NO
   CLARIFICATION_REQUIRED: NO
   ```

No CP-03 is created and no false recovery occurs.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the annotated Mermaid
architecture diagram.

## Google technologies and production stack

- Google ADK
- Gemini 3.5 Flash on Vertex AI
- Google Cloud Run
- Cloud Firestore
- FastAPI
- HTML, CSS, and Vanilla JavaScript
- Read-only GitHub evidence

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.server:app --reload --port 8000
```

Copy `.env.example` to a private `.env`, configure a Google Cloud project, and
authenticate with Google Application Default Credentials. Do not put API keys,
tokens, service-account files, or proxy settings in the public repository.

## Cloud Run deployment outline

Cloud Run uses an attached service account and the Vertex configuration in
`.env.example`. Deployment should follow credential, Firestore, GitHub, and
smoke-test verification. The outline is in [DEPLOYMENT.md](DEPLOYMENT.md);
this repository-preparation step does not deploy.

## State integrity and evidence cursor

Observed evidence is normalized before interpretation. The current Trusted
State's evidence cursor defines where subsequent evidence retrieval begins.
Only `prepare_resume_state` can commit a new Trusted State and checkpoint.

## MVP scope and limitations

STATEWAKE is a controlled interrupted-work recovery workflow, not a general
project manager. Evidence does not establish approval, and recovery cannot
proceed without explicit human authorization when a protected direction is in
conflict. Live external tests require Google Cloud and GitHub access.

## Testing

The test suite covers ADK session lifecycle and transient retry handling,
validity output, evidence normalization, Decision Gate authorization, atomic
state transitions, idempotency, memory boundaries, API serving, UI structure,
and Vertex configuration. External-environment tests are reported separately
when credentials or network access are unavailable.
