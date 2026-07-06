import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Values that are placeholders, not real keys — treated as "no key".
_PLACEHOLDERS = {
    "", "gsk_your_key_here", "gsk_your_real_key_here", "your_key_here",
    "gsk_xxxxxxxxxxxxxxxxxxxx", "gsk_xxx", "changeme",
    "lsv2_pt_your_key_here",
    "lsv2_pt_xxxxxxxxx",
}


def _candidate_env_paths():
    """Files we will try to load, in priority order."""
    names_real = [".env", ".env.txt", ".env.local"]
    dirs = [BASE_DIR, os.getcwd()]
    paths = []
    for d in dirs:
        for n in names_real:
            paths.append(os.path.join(d, n))
    # last resort: the example file, in case the key was typed there directly
    for d in dirs:
        paths.append(os.path.join(d, ".env.example"))
    # de-duplicate, keep order
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

ENV_FILE = ""
ENV_SEARCHED = []
for _p in _candidate_env_paths():
    exists = os.path.isfile(_p)
    ENV_SEARCHED.append((_p, exists))
    if exists and not ENV_FILE:
        load_dotenv(_p, override=False)
        ENV_FILE = _p


def _clean(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


# ---- Paths -----------------------------------------------------------------
DB_PATH = os.path.join(BASE_DIR, "smartrfp.db")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ---- Groq LLM --------------------------------------------------------------
GROQ_API_KEY = _clean(os.getenv("GROQ_API_KEY", ""))
if GROQ_API_KEY in _PLACEHOLDERS:
    GROQ_API_KEY = ""

GROQ_MODEL = _clean(os.getenv("GROQ_MODEL", "")) or "openai/gpt-oss-20b"

# ---- LangSmith -------------------------------------------------------------

LANGSMITH_API_KEY = _clean(os.getenv("LANGSMITH_API_KEY", ""))
if LANGSMITH_API_KEY in _PLACEHOLDERS:
    LANGSMITH_API_KEY = ""

LANGSMITH_PROJECT = (
    _clean(os.getenv("LANGSMITH_PROJECT", ""))
    or "SmartRFP"
)

LANGSMITH_ENDPOINT = (
    _clean(os.getenv("LANGSMITH_ENDPOINT", ""))
    or "https://api.smith.langchain.com"
)

LANGSMITH_TRACING = (
    _clean(os.getenv("LANGSMITH_TRACING", "true")).lower()
    == "true"
)

APP_NAME = "SmartRFP"
APP_TAGLINE = "AI-Powered RFP Analysis & Proposal Intelligence"
MAX_UPLOAD_MB = 50
SUPPORTED_TYPES = ["pdf", "docx", "txt"]

REVIEWER_ROLES = ["Junior Reviewer", "Senior Reviewer", "Supervisor", "SME (Subject Matter Expert)"]
STATUSES = ["Uploaded", "Drafting", "In Review", "Approved", "Rejected"]
RAG_TOP_K = 3
