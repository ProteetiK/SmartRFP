import os
from dotenv import load_dotenv

# frontend/ directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env from project root first, then frontend/.env if present
PROJECT_ROOT = os.path.dirname(BASE_DIR)

for env_file in (
    os.path.join(PROJECT_ROOT, ".env"),
    os.path.join(BASE_DIR, ".env"),
):
    if os.path.isfile(env_file):
        load_dotenv(env_file, override=False)


def _clean(value: str) -> str:
    """Remove whitespace and surrounding quotes."""
    value = (value or "").strip()

    if len(value) >= 2 and value[0] == value[-1]:
        if value[0] in ("'", '"'):
            value = value[1:-1].strip()

    return value


# ------------------------------------------------------------------ #
# App / UI
# ------------------------------------------------------------------ #

APP_NAME = "SmartRFP"

APP_TAGLINE = (
    "AI-Powered RFP Analysis & Proposal Intelligence"
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
)

DEBUG = (
    os.getenv("DEBUG", "false").lower() == "true"
)


# ------------------------------------------------------------------ #
# LLM display/configuration
# ------------------------------------------------------------------ #
# The frontend may need the model name for the Settings page.
# The actual LLM API key and LLM calls remain in the backend.

GROQ_MODEL = _clean(
    os.getenv(
        "GROQ_MODEL",
        "llama-3.1-8b-instant",
    )
)

OPENAI_MODEL = _clean(
    os.getenv(
        "OPENAI_MODEL",
        "gpt-4o-mini",
    )
)


# ------------------------------------------------------------------ #
# Frontend <-> Backend
# ------------------------------------------------------------------ #

SMARTRFP_API_URL = _clean(
    os.getenv(
        "SMARTRFP_API_URL",
        "http://localhost:8000",
    )
).rstrip("/")

SMARTRFP_API_KEY = _clean(
    os.getenv(
        "SMARTRFP_API_KEY",
        "",
    )
)


# ------------------------------------------------------------------ #
# File upload
# ------------------------------------------------------------------ #

MAX_UPLOAD_MB = 50

SUPPORTED_TYPES = [
    "pdf",
    "docx",
    "txt",
]


# ------------------------------------------------------------------ #
# Review
# ------------------------------------------------------------------ #

REVIEWER_ROLES = [
    "Junior Reviewer",
    "Senior Reviewer",
    "Supervisor",
    "SME (Subject Matter Expert)",
]

STATUSES = [
    "Uploaded",
    "Drafting",
    "In Review",
    "Approved",
    "Rejected",
]


# ------------------------------------------------------------------ #
# RAG UI settings
# ------------------------------------------------------------------ #
# Only keep this here if the frontend displays/controls RAG top-k.
# Actual RAG retrieval remains backend-side.

RAG_TOP_K = 3


# ------------------------------------------------------------------ #
# Frontend paths
# ------------------------------------------------------------------ #

DB_PATH = os.path.join(
    BASE_DIR,
    "smartrfp.db",
)

EXPORT_DIR = os.path.join(
    BASE_DIR,
    "exports",
)

os.makedirs(EXPORT_DIR, exist_ok=True)