import os
import requests
import streamlit as st

BASE = os.getenv("SMARTRFP_API_URL", "http://localhost:8000").rstrip("/")
st.write(BASE)
TIMEOUT = 600  # analysis can take a while (embeddings + several LLM calls)
API_KEY = os.getenv("SMARTRFP_API_KEY", "")

# Reusing a single TCP session avoids the connect/TLS handshake cost on every
# single page rerun, which is what was pushing page loads past 5s.
_session = requests.Session()
_session.headers.update({"Connection": "keep-alive"})
if API_KEY:
    _session.headers.update({"X-API-Key": API_KEY})


class APIError(RuntimeError):
    pass


def _url(path):
    return f"{BASE}{path}"


def _auth_headers():
    return {"X-API-Key": API_KEY} if API_KEY else {}


def _get(path, **kw):
    r = _session.get(_url(path), timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=5, show_spinner=False)
def _get_cached(path):
    """Cache read-only GETs for a short TTL so page navigation inside the same
    5s window is instant instead of round-tripping to the backend + DB every
    single Streamlit rerun. Any mutating call below clears this cache so the
    UI never shows stale data after an upload/edit/status change."""
    return _get(path)


def clear_cache():
    _get_cached.clear()


def _safe(path, default):
    """Read-only GET for DISPLAY. A backend error must never crash a page during
    a demo — degrade to a sensible empty default instead of raising."""
    try:
        return _get_cached(path)
    except Exception:
        return default


def _post(path, **kw):
    headers = {**_auth_headers(), **kw.pop("headers", {})}
    r = requests.post(_url(path), timeout=TIMEOUT, headers=headers, **kw)
    if r.status_code >= 400:
        try:
            raise APIError(r.json().get("detail", r.text))
        except ValueError:
            raise APIError(r.text)
    return r.json()


def _put(path, **kw):
    headers = {**_auth_headers(), **kw.pop("headers", {})}
    r = requests.put(_url(path), timeout=TIMEOUT, headers=headers, **kw)
    r.raise_for_status()
    return r.json()


def _delete(path, **kw):
    headers = {**_auth_headers(), **kw.pop("headers", {})}
    r = requests.delete(_url(path), timeout=TIMEOUT, headers=headers, **kw)
    r.raise_for_status()
    return r.json()


# ---- health ---- #
def backend_up():
    try:
        _get("/health")
        return True
    except Exception:
        return False


def llm_status():
    try:
        return _get("/health/llm")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "model": "?", "message": str(exc)}


def ready():
    try:
        return _get("/health/ready")
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}


# ---- rfps ---- #
def list_rfps():
    return _safe("/rfps", [])


def get_rfp(rfp_id):
    return _safe(f"/rfps/{rfp_id}", None)


def delete_rfp(rfp_id):
    result = _delete(f"/rfps/{rfp_id}")
    clear_cache()
    return result


def upload_rfp(filename, file_bytes, deal_name="", client_name="", region="",
               deadline="", assigned_role="", use_web_search=True):
    files = {"file": (filename, file_bytes)}
    data = {"deal_name": deal_name, "client_name": client_name, "region": region,
            "deadline": deadline, "assigned_role": assigned_role,
            "use_web_search": str(use_web_search).lower()}
    result = _post("/upload-rfp", files=files, data=data)
    clear_cache()
    return result


def regenerate(rfp_id):
    result = _post("/regenerate", json={"rfp_id": rfp_id})
    clear_cache()
    return result


# ---- children ---- #
def get_requirements(rfp_id):
    return _safe(f"/requirements/{rfp_id}", [])


def get_draft_sections(rfp_id):
    return _safe(f"/draft/{rfp_id}", [])


def update_draft_section(section_id, content):
    result = _put(f"/draft-section/{section_id}", json={"content": content})
    clear_cache()
    return result


def get_pricing(rfp_id):
    return _safe(f"/pricing/{rfp_id}", [])


def get_evaluation_metrics(rfp_id):
    data = _safe(f"/evaluation/{rfp_id}", None)
    return data or None


def get_audit_log(rfp_id):
    return _safe(f"/audit/{rfp_id}", [])


def log_action(rfp_id, action, actor, detail=""):
    result = _post(f"/audit/{rfp_id}", json={"action": action, "actor": actor, "detail": detail})
    clear_cache()
    return result


def set_status(rfp_id, status, detail=""):
    result = _put(f"/review/{rfp_id}", json={"status": status, "detail": detail})
    clear_cache()
    return result


# ---- kb ---- #
def kb():
    return _safe("/kb", {"count": 0, "docs": []})


def kb_count():
    return kb().get("count", 0)


def get_kb_docs():
    return kb().get("docs", [])


def add_kb_doc(title, doc_type, content):
    result = _post("/kb", json={"title": title, "doc_type": doc_type, "content": content})
    clear_cache()
    return result


# ---- export ---- #
def export_bytes(rfp_id, fmt):
    r = requests.get(_url(f"/export/{rfp_id}"), params={"fmt": fmt}, timeout=TIMEOUT,
                     headers=_auth_headers())
    r.raise_for_status()
    return r.content


def get_export_history(rfp_id):
    return _safe(f"/export/{rfp_id}/history", {"exports": []})


def debug_retrieval(rfp_id):
    """Live diagnostic: real Pinecone vector counts + raw similarity scores
    for this RFP, explaining exactly why retrieval is/isn't finding documents."""
    return _get(f"/debug/retrieval/{rfp_id}")
