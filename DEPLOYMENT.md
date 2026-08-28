# STATEWAKE Cloud Run preparation

## Production shape

One FastAPI service serves the STATEWAKE frontend and API:

- `/` serves `ui/index.html`
- `/static/*` serves the frontend CSS and JavaScript
- `/api/*` serves the existing FastAPI API

The frontend uses same-origin `/api/*` by default. An explicit `api` query
parameter or `STATEWAKE_API_BASE` value is available only for local development
overrides.

## Runtime configuration names

Configure these names through the deployment environment; do not commit values:

- `GOOGLE_CLOUD_PROJECT`
- `STATEWAKE_GEMINI_MODEL`
- `STATEWAKE_ADK_APP_NAME`
- `STATEWAKE_ADK_USER_ID`
- `STATEWAKE_ADK_SESSION_ID`
- `GITHUB_TOKEN`

Cloud Run Firestore access uses the service account's Application Default
Credentials. Local ADC files, GitHub CLI credentials, and local proxy variables
are not packaged or required by the container.

The runtime service account needs least-privilege Firestore read/write access
for the existing Trusted State, checkpoint, and re-entry session collections.
IAM changes are intentionally not performed while billing is disabled.

## Future host deployment command

Run only after billing is enabled and the deployment preflight passes:

```powershell
gcloud run deploy statewake `
  --source . `
  --project statewake-agentic-2026 `
  --region us-central1 `
  --allow-unauthenticated
```
