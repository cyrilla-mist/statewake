# STATEWAKE Cloud Run Deployment Reference

STATEWAKE has a public Google Cloud Run deployment:

<https://statewake-73198201224.us-central1.run.app>

This document records the deployment shape and configuration contract for future redeployment or maintenance. It is no longer a pre-deployment checklist.

## Production shape

One FastAPI service serves the STATEWAKE frontend and API:

- `/` serves `ui/index.html`
- `/static/*` serves the frontend CSS and JavaScript
- `/api/*` serves the FastAPI API

The frontend uses same-origin `/api/*` by default. An explicit `api` query parameter or `STATEWAKE_API_BASE` value is available only for local development overrides.

## Runtime configuration names

Configure these values through the deployment environment; do not commit secrets or machine-local credentials:

- `GOOGLE_CLOUD_PROJECT`
- `STATEWAKE_GEMINI_MODEL`
- `STATEWAKE_ADK_APP_NAME`
- `STATEWAKE_ADK_USER_ID`
- `STATEWAKE_ADK_SESSION_ID`
- `GITHUB_TOKEN`

Cloud Run / Firestore access should use the service account attached to the runtime rather than local credential files packaged into the container.

The runtime service account should have only the permissions required by the existing Trusted State, checkpoint, and re-entry session workflow.

## Redeployment outline

Before redeploying, confirm that:

1. local tests pass;
2. the intended Google Cloud project and region are selected;
3. required environment variables and service-account permissions exist;
4. no `.env`, local ADC file, GitHub CLI credential, token, or proxy-specific secret is included in the build context;
5. the deployed service passes a basic UI/API smoke test after rollout.

Source deployment can use the existing Cloud Run shape, for example:

```powershell
gcloud run deploy statewake `
  --source . `
  --project statewake-agentic-2026 `
  --region us-central1 `
  --allow-unauthenticated
```

Treat the project ID above as this repository's historical deployment configuration, not as a reusable value for unrelated deployments.

## Security notes

- Keep GitHub access read-only for evidence collection where the product contract requires read-only evidence.
- Do not place API keys or service-account JSON in tracked files.
- Prefer runtime identity / Application Default Credentials for Google Cloud services.
- Re-check least-privilege IAM before changing the Firestore schema or adding new external actions.

## Demo scenario note

The STATEWAKE demo may contain project-state text about resolving a Cloud Run deployment failure. That text belongs to the **external demo project's recovery scenario** and should not be confused with the deployment status of STATEWAKE itself.
