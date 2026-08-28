import os

from dotenv import load_dotenv


load_dotenv()


GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


# Current ADK uses Enterprise as the authoritative Google Cloud/Vertex
# selector. Normalize it before any module creates an ADK model.
GOOGLE_GENAI_USE_ENTERPRISE = _env_flag("GOOGLE_GENAI_USE_ENTERPRISE")
if GOOGLE_GENAI_USE_ENTERPRISE:
    os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "1"

# Kept for compatibility with older google-genai configuration, but it must
# never select the production backend by itself.
GOOGLE_GENAI_USE_VERTEXAI = _env_flag("GOOGLE_GENAI_USE_VERTEXAI")

GEMINI_MODEL = os.getenv(
    "STATEWAKE_GEMINI_MODEL",
    "gemini-3.5-flash",
)


def validate_vertex_configuration() -> None:
    """Validate the production Vertex AI configuration contract."""

    if not GOOGLE_GENAI_USE_ENTERPRISE:
        raise RuntimeError(
            "Vertex AI Enterprise mode is required: set "
            "GOOGLE_GENAI_USE_ENTERPRISE=1."
        )
    if not GOOGLE_CLOUD_PROJECT:
        raise RuntimeError(
            "Google Cloud project is required: set GOOGLE_CLOUD_PROJECT."
        )
    if not GOOGLE_CLOUD_LOCATION:
        raise RuntimeError(
            "Google Cloud location is required: set GOOGLE_CLOUD_LOCATION."
        )


def get_model_backend() -> str:
    """Return the configured production backend without consulting API keys."""

    return "VERTEX_AI" if GOOGLE_GENAI_USE_ENTERPRISE else "UNCONFIGURED"

ADK_APP_NAME = os.getenv(
    "STATEWAKE_ADK_APP_NAME",
    "statewake",
)

ADK_USER_ID = os.getenv(
    "STATEWAKE_ADK_USER_ID",
    "demo-user",
)

ADK_SESSION_ID = os.getenv(
    "STATEWAKE_ADK_SESSION_ID",
    "reentry-session-01",
)


# ============================================================
# FIRESTORE
# ============================================================

FIRESTORE_PROJECTS_COLLECTION = os.getenv(
    "STATEWAKE_PROJECTS_COLLECTION",
    "projects",
)

FIRESTORE_CHECKPOINTS_SUBCOLLECTION = (
    "checkpoints"
)

FIRESTORE_REENTRY_SESSIONS_SUBCOLLECTION = (
    "reentrySessions"
)

DEMO_PROJECT_ID = "statewake-demo"

DEMO_HERO_SESSION_ID = "session-hero-01"

DEMO_HERO_CURRENT_SHA = (
    "fb5fcbfefcafef17256eab8dd4227349c1119031"
)
# ============================================================
# GITHUB
# ============================================================

GITHUB_OWNER = "cyrilla-mist"
GITHUB_REPO = "statewake-demo-project"
GITHUB_BRANCH = "main"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HERO_BASELINE_SHA = (
    "ad23bfdca4001f5d7a70dc2a3d845ea6b6db780f"
)
