import os

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

#BASE = os.getenv("SMARTRFP_API_URL", "https://smartrfp-production.up.railway.app").rstrip("/")
BASE = os.getenv("SMARTRFP_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 600
API_KEY = os.getenv("SMARTRFP_API_KEY", "")


# --------------------------------------------------------------------
# Shared HTTP session
# --------------------------------------------------------------------

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "PUT", "DELETE"],
)

adapter = HTTPAdapter(
    pool_connections=50,
    pool_maxsize=50,
    max_retries=retry,
)

_session = requests.Session()
_session.mount("http://", adapter)
_session.mount("https://", adapter)

_session.headers.update({
    "Connection": "keep-alive",
})

if API_KEY:
    _session.headers.update({
        "X-API-Key": API_KEY,
    })


class APIError(RuntimeError):
    pass


def _url(path):
    return f"{BASE}{path}"


def _auth_headers():
    return {"X-API-Key": API_KEY} if API_KEY else {}


def _request(method, path, **kwargs):
    headers = {**_auth_headers(), **kwargs.pop("headers", {})}

    response = _session.request(
        method=method,
        url=_url(path),
        timeout=TIMEOUT,
        headers=headers,
        **kwargs,
    )

    if response.status_code >= 400:
        try:
            raise APIError(response.json().get("detail", response.text))
        except ValueError:
            raise APIError(response.text)

    return response


def _get(path, **kwargs):
    return _request("GET", path, **kwargs).json()


def _post(path, **kwargs):
    return _request("POST", path, **kwargs).json()


def _put(path, **kwargs):
    return _request("PUT", path, **kwargs).json()


def _delete(path, **kwargs):
    return _request("DELETE", path, **kwargs).json()


@st.cache_data(ttl=5, show_spinner=False)
def _get_cached(path):
    """
    Cache read-only GETs for a short TTL.
    """
    return _get(path)


def clear_cache():
    _get_cached.clear()


def _safe(path, default):
    try:
        return _get_cached(path)
    except Exception:
        return default


# --------------------------------------------------------------------
# Health
# --------------------------------------------------------------------

def backend_up():
    try:
        _get("/health")
        return True
    except Exception:
        return False


def llm_status():
    try:
        return _get("/health/llm")
    except Exception as exc:
        return {
            "ok": False,
            "model": "llama-3.1-8b-instant",
            "message": str(exc),
        }


def ready():
    try:
        return _get("/health/ready")
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


# --------------------------------------------------------------------
# RFPs
# --------------------------------------------------------------------

def list_rfps():
    return _safe("/rfps", [])


def get_rfp(rfp_id):
    return _safe(f"/rfps/{rfp_id}", None)


def delete_rfp(rfp_id):
    result = _delete(f"/rfps/{rfp_id}")
    clear_cache()
    return result


def upload_rfp(
    filename,
    file_bytes,
    deal_name="",
    client_name="",
    region="",
    deadline="",
    assigned_role="",
    use_web_search=True,
):
    files = {
        "file": (filename, file_bytes),
    }

    data = {
        "deal_name": deal_name,
        "client_name": client_name,
        "region": region,
        "deadline": deadline,
        "assigned_role": assigned_role,
        "use_web_search": str(use_web_search).lower(),
    }

    result = _post(
        "/upload-rfp",
        files=files,
        data=data,
    )

    clear_cache()
    return result


def regenerate(rfp_id):
    result = _post(
        "/regenerate",
        json={"rfp_id": rfp_id},
    )

    clear_cache()
    return result


# --------------------------------------------------------------------
# Requirements / Draft
# --------------------------------------------------------------------

def get_requirements(rfp_id):
    return _safe(f"/requirements/{rfp_id}", [])


def get_draft_sections(rfp_id):
    return _safe(f"/draft/{rfp_id}", [])


def update_draft_section(section_id, content):
    result = _put(
        f"/draft-section/{section_id}",
        json={"content": content},
    )

    clear_cache()
    return result

def update_pricing(rfp_id, pricing_lines):
    result = _put(
        f"/pricing/{rfp_id}",
        json={"pricing": pricing_lines},
    )

    clear_cache()
    return result

# --------------------------------------------------------------------
# Pricing / Evaluation
# --------------------------------------------------------------------

def get_pricing(rfp_id):
    return _safe(f"/pricing/{rfp_id}", [])


def get_evaluation_metrics(rfp_id):
    data = _safe(f"/evaluation/{rfp_id}", None)
    return data or None

def get_trace_latencies(rfp_id):
    return _safe(f"/evaluation/{rfp_id}/latencies", {})

# --------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------

def get_audit_log(rfp_id):
    return _safe(f"/audit/{rfp_id}", [])


def log_action(rfp_id, action, actor, detail=""):
    result = _post(
        f"/audit/{rfp_id}",
        json={
            "action": action,
            "actor": actor,
            "detail": detail,
        },
    )

    clear_cache()
    return result


def set_status(rfp_id, status, detail=""):
    result = _put(
        f"/review/{rfp_id}",
        json={
            "status": status,
            "detail": detail,
        },
    )

    clear_cache()
    return result


# --------------------------------------------------------------------
# Knowledge Base
# --------------------------------------------------------------------

def kb():
    return _safe(
        "/kb",
        {
            "count": 0,
            "docs": [],
        },
    )


def kb_count():
    return kb().get("count", 0)


def get_kb_docs():
    return kb().get("docs", [])


def add_kb_doc(title, doc_type, content):
    result = _post(
        "/kb",
        json={
            "title": title,
            "doc_type": doc_type,
            "content": content,
        },
    )

    clear_cache()
    return result


# --------------------------------------------------------------------
# Export
# --------------------------------------------------------------------

def export_bytes(rfp_id, fmt):
    response = _request(
        "GET",
        f"/export/{rfp_id}",
        params={"fmt": fmt},
    )

    return response.content


def get_export_history(rfp_id):
    return _safe(
        f"/export/{rfp_id}/history",
        {"exports": []},
    )


# --------------------------------------------------------------------
# Debug
# --------------------------------------------------------------------

def debug_retrieval(rfp_id):
    """
    Live diagnostic: real Pinecone vector counts + raw similarity scores.
    """
    return _get(f"/debug/retrieval/{rfp_id}")
    
def get_trace_latencies(rfp_id):
    data = _safe(
        f"/evaluation/{rfp_id}/latencies",
        {"trace_id": None, "latencies": {}},
    )

    return data or {
        "trace_id": None,
        "latencies": {},
    }