# STATEWAKE local development helper only.
# These variables apply to this PowerShell process and its child processes.
# Cloud Run and production configuration do not depend on this file.

if (Test-Path -LiteralPath ".\.venv\Scripts\Activate.ps1") {
  . ".\.venv\Scripts\Activate.ps1"
}

$env:grpc_proxy = "http://127.0.0.1:7897"
$env:https_proxy = "http://127.0.0.1:7897"
$env:http_proxy = "http://127.0.0.1:7897"

Write-Host "STATEWAKE local development proxy settings applied to this session."
if (Get-Command gh -ErrorAction SilentlyContinue) {
  $githubToken = gh auth token 2>$null
  if ($LASTEXITCODE -eq 0 -and $githubToken) {
    $env:GITHUB_TOKEN = $githubToken
    Write-Host "GitHub token available to this process: YES"
  } else {
    Write-Host "GitHub token available to this process: NO"
  }
} else {
  Write-Host "GitHub CLI unavailable; set GITHUB_TOKEN manually for authenticated access."
}
Write-Host "Starting API with: python -m uvicorn app.server:app --reload"
