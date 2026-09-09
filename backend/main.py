import io
import logging
import os

from dotenv import load_dotenv, find_dotenv

from backend.langsmith_utils import (
    get_trace_id_for_rfp,
    get_trace_latencies,
)

load_dotenv(find_dotenv())

if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and not os.getenv("LANGCHAIN_API_KEY", "").strip():
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logging.getLogger("smartrfp.api").warning(
        "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY is not set — "
        "disabling LangSmith tracing for this run."
    )

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import Base, engine, get_db
from backend import crud
from backend.services import analyze_rfp, regenerate_pipeline, human_review
from backend.security import limiter, require_api_key, require_role
from backend.guardrails import GuardrailViolation
from backend.metrics import AUTH_FAILURES, RATE_LIMIT_REJECTIONS
from backend.utils.exporter import export_txt, export_docx, export_pdf



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartrfp.api")

app = FastAPI(title="SmartRFP API", version="2.0.0")

if settings.ENVIRONMENT == "production":
    if "*" in settings.ALLOWED_ORIGINS:
        raise RuntimeError(
            "ALLOWED_ORIGINS=* is not permitted when ENVIRONMENT=production. "
            "Set ALLOWED_ORIGINS to your actual frontend origin(s).")
    if not settings.API_KEYS:
        raise RuntimeError(
            "ENVIRONMENT=production requires at least one API key in API_KEYS.")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def _security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        # Only set HSTS in production — it tells browsers to refuse HTTP for
        # a year, which is actively harmful during local http:// development.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(GuardrailViolation)
async def guardrail_violation_handler(request: Request, exc: GuardrailViolation):
    logger.warning("Guardrail violation (%s) on %s: %s", exc.rule, request.url.path, exc)
    return Response(
        content=f'{{"detail": "{str(exc)}", "guardrail_rule": "{exc.rule}"}}',
        status_code=400, media_type="application/json",
    )


@app.middleware("http")
async def _auth_metrics_middleware(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        AUTH_FAILURES.inc()
    elif response.status_code == 429:
        RATE_LIMIT_REJECTIONS.inc()
    return response

SEED_KB = [
    ("Security & Compliance Guide", "Policy",
     "Our platform supports SSO, MFA, encryption at rest and in transit, RBAC, "
     "audit logging, and aligns with ISO 27001 and SOC 2 control families."),
    ("Cloud Migration Playbook", "Guide",
     "Migration follows assessment, planning, execution, and validation phases "
     "with rollback plans and parallel-run cutover."),
    ("Managed Support Handbook", "Process",
     "Tiered managed support with defined response targets, incident management, "
     "and continuous monitoring."),
]


def _migrate_columns(table_name: str, new_cols: dict):
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns(table_name)}
    with engine.begin() as conn:
        for col, coltype in new_cols.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE {table_name} ADD COLUMN {col} {coltype}"))
                logger.info("Migrated: added %s.%s", table_name, col)


def _migrate_ragas_columns():
    _migrate_columns("evaluation_metrics", {
        "ragas_faithfulness": "FLOAT", "ragas_answer_relevancy": "FLOAT",
        "ragas_context_precision": "FLOAT", "ragas_context_recall": "FLOAT",
        "ragas_evaluated_at": "VARCHAR",
        "ragas_status": "VARCHAR", "ragas_error": "VARCHAR",
        "ragas_attempts": "INTEGER", "below_threshold": "INTEGER",
        "threshold_notes": "VARCHAR", "stage_latencies_json": "VARCHAR",
        "retrieved_docs_count": "INTEGER",
        "quality_completeness": "FLOAT",
    })
    _migrate_columns("knowledge_base", {
        "pinecone_indexed": "INTEGER",
    })


def _ingest_kb_doc_safe(kb_id: int, title: str, doc_type: str, content: str) -> bool:
    try:
        from backend.rag.ingestion import DocumentIngestion
        DocumentIngestion().ingest_kb_document(kb_id, title, doc_type, content)
        return True
    except Exception:
        logger.exception("Failed to embed KB doc id=%s into Pinecone; it will "
                         "still show in /kb but won't be searchable until "
                         "re-synced.", kb_id)
        return False


@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)
    _migrate_ragas_columns()
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        if crud.kb_count(db) == 0:
            for title, dtype, content in SEED_KB:
                kb_id = crud.add_kb_doc(db, title, dtype, content)
                if _ingest_kb_doc_safe(kb_id, title, dtype, content):
                    crud.mark_kb_indexed(db, kb_id)
            logger.info("Seeded %d knowledge-base documents.", len(SEED_KB))

        pending = crud.get_kb_docs_unindexed(db)
        if pending:
            logger.info("Found %d KB doc(s) not yet indexed in Pinecone; syncing...", len(pending))
            synced = 0
            for doc in pending:
                if _ingest_kb_doc_safe(doc["id"], doc["title"], doc["doc_type"], doc["content"]):
                    crud.mark_kb_indexed(db, doc["id"])
                    synced += 1
            logger.info("KB->Pinecone sync: %d/%d succeeded.", synced, len(pending))
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "SmartRFP API running"}


# ------------------------------- Health ---------------------------------- #
@app.get("/health")
def health():
    return {"status": "healthy"}


#@app.get("/health/llm")
#def health_llm():
#    return api.llm_status()


@app.get("/health/ready")
def health_ready():
    try:
        from backend.rag.pinecone_client import get_pinecone_manager
        pc = get_pinecone_manager().health_check()
    except Exception as exc:  # noqa: BLE001
        pc = {"status": "error", "message": str(exc)}
    overall = "healthy" if pc.get("status") == "healthy" else "degraded"
    return {"status": overall, "components": {"vector_store": pc}}


@app.get("/debug/retrieval/{rfp_id}")
def debug_retrieval(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    from backend.rag.vector_store import VectorStore
    from backend.rag.utils import rfp_namespace, KB_NAMESPACE

    rfp = crud.get_rfp(db, rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    requirements = crud.get_requirements(db, rfp_id)
    reqs_list = [r["text"] for r in requirements[:14]]
    query = " ".join(reqs_list)[:800].strip() or \
        "technical solution security compliance implementation deliverables timeline"

    store = VectorStore()
    ns = rfp_namespace(rfp_id)

    report = {"rfp_id": rfp_id, "query_used": query, "rag_score_threshold": settings.RAG_SCORE_THRESHOLD}

    try:
        stats = store.describe()
        namespaces = getattr(stats, "namespaces", None) or (stats.get("namespaces", {}) if isinstance(stats, dict) else {})
        for label, namespace in (("rfp_namespace", ns), ("kb_namespace", KB_NAMESPACE)):
            ns_stats = namespaces.get(namespace)
            count = getattr(ns_stats, "vector_count", None) if ns_stats is not None else None
            if count is None and isinstance(ns_stats, dict):
                count = ns_stats.get("vector_count")
            report[f"{label}_name"] = namespace
            report[f"{label}_vector_count"] = int(count or 0)
    except Exception as exc:  # noqa: BLE001
        report["index_stats_error"] = str(exc)

    for label, namespace in (("rfp_namespace_raw_results", ns), ("kb_namespace_raw_results", KB_NAMESPACE)):
        try:
            docs = store.similarity_search(query, top_k=5, namespace=namespace)
            report[label] = [
                {"score": round(d.metadata.get("score", 0), 4),
                "passes_threshold": d.metadata.get("score", 0) >= settings.RAG_SCORE_THRESHOLD,
                "snippet": (d.page_content or "")[:150]}
                for d in docs
            ]
        except Exception as exc:  # noqa: BLE001
            report[label] = f"error: {exc}"

    diagnosis = []
    if report.get("rfp_namespace_vector_count", 0) == 0:
        diagnosis.append(
            "rfp_namespace_vector_count is 0 — ingestion never wrote vectors for this RFP, or "
            "they were deleted. Check backend logs for 'Ingestion:' around when this RFP was "
            "analyzed, and confirm PINECONE_API_KEY/PINECONE_INDEX_NAME are correct.")
    elif report.get("rfp_namespace_raw_results") and all(
            not r.get("passes_threshold", False) for r in report["rfp_namespace_raw_results"] if isinstance(r, dict)):
        diagnosis.append(
            "Vectors exist, but none score above RAG_SCORE_THRESHOLD for this query — see the raw "
            "scores above. Consider lowering RAG_SCORE_THRESHOLD in .env, or the requirements "
            "extracted from this RFP may be too generic/short to match its own indexed chunks well.")
    elif report.get("rfp_namespace_raw_results") and any(
            r.get("passes_threshold", False) for r in report["rfp_namespace_raw_results"] if isinstance(r, dict)):
        diagnosis.append(
            "At least one result passes the threshold — retrieval should be working for this RFP. "
            "If the AI Evaluation page still shows 0, that row is stale; click Regenerate.")
    report["diagnosis"] = diagnosis or ["Could not form a diagnosis from the data above — inspect manually."]

    return report


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ------------------------------- Upload ---------------------------------- #
@app.post("/upload-rfp")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_rfp(
    request: Request,
    file: UploadFile = File(...),
    deal_name: str = Form(""), client_name: str = Form(""),
    region: str = Form(""), deadline: str = Form(""),
    assigned_role: str = Form(""), use_web_search: bool = Form(True),
    _auth: str = Depends(require_api_key),
):
    try:
        result = await analyze_rfp(
            file=file, deal_name=deal_name, client_name=client_name,
            region=region, deadline=deadline, assigned_role=assigned_role,
            use_web_search=use_web_search)
        return JSONResponse(content=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("upload-rfp failed")
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}")


# ------------------------------- RFPs ------------------------------------ #
@app.get("/rfps")
def list_rfps(db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    return crud.list_rfps(db)


@app.get("/rfps/{rfp_id}")
def get_rfp(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    rfp = crud.get_rfp(db, rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@app.delete("/rfps/{rfp_id}")
def delete_rfp(rfp_id: int, db: Session = Depends(get_db), _role: str = Depends(require_role("admin"))):
    crud.delete_rfp(db, rfp_id)
    return {"success": True}


@app.get("/requirements/{rfp_id}")
def get_requirements(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    return crud.get_requirements(db, rfp_id)


@app.get("/draft/{rfp_id}")
def get_draft(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    return crud.get_draft_sections(db, rfp_id)


class SectionEdit(BaseModel):
    content: str


@app.put("/draft-section/{section_id}")
def update_draft_section(section_id: int, body: SectionEdit, db: Session = Depends(get_db), _role: str = Depends(require_role("reviewer", "admin"))):
    crud.update_draft_section(db, section_id, body.content)
    return {"success": True}


@app.get("/pricing/{rfp_id}")
def get_pricing(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    return crud.get_pricing(db, rfp_id)


@app.get("/evaluation/{rfp_id}")
def get_evaluation(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    try:
        return crud.get_evaluation_metrics(db, rfp_id) or {}
    except Exception:
        logger.exception("evaluation read failed for rfp_id=%s; attempting self-heal", rfp_id)
        try:
            db.rollback()
        except Exception:
            pass
        try:
            _migrate_ragas_columns()
            return crud.get_evaluation_metrics(db, rfp_id) or {}
        except Exception:
            logger.exception("evaluation read still failing after migrate; returning empty")
            try:
                db.rollback()
            except Exception:
                pass
            return {}


@app.get("/audit/{rfp_id}")
def get_audit(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    return crud.get_audit_log(db, rfp_id)


class AuditEntry(BaseModel):
    action: str
    actor: str
    detail: str = ""


@app.post("/audit/{rfp_id}")
def add_audit(rfp_id: int, body: AuditEntry, db: Session = Depends(get_db), _role: str = Depends(require_role("reviewer", "admin"))):
    crud.log_action(db, rfp_id, body.action, body.actor, body.detail)
    return {"success": True}


class StatusUpdate(BaseModel):
    status: str
    detail: str = ""


@app.put("/review/{rfp_id}")
def review(rfp_id: int, body: StatusUpdate, _role: str = Depends(require_role("reviewer", "admin"))):
    return human_review(rfp_id, body.status, body.detail)


class RegenerateBody(BaseModel):
    rfp_id: int


@app.post("/regenerate")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
def regenerate(request: Request, body: RegenerateBody, _role: str = Depends(require_role("reviewer", "admin"))):
    try:
        return regenerate_pipeline(body.rfp_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}")


# ------------------------------- KB -------------------------------------- #
@app.get("/kb")
def kb(db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    docs = crud.get_kb_docs(db)
    indexed = sum(1 for d in docs if d.get("pinecone_indexed"))
    return {
        "count": crud.kb_count(db),
        "docs": docs,
        "indexed_in_pinecone": indexed,
        "not_yet_searchable": crud.kb_count(db) - indexed,
    }


class KBDoc(BaseModel):
    title: str
    doc_type: str = "reference"
    content: str


@app.post("/kb")
def add_kb(body: KBDoc, db: Session = Depends(get_db), _role: str = Depends(require_role("admin"))):
    kb_id = crud.add_kb_doc(db, body.title, body.doc_type, body.content)
    indexed = _ingest_kb_doc_safe(kb_id, body.title, body.doc_type, body.content)
    if indexed:
        crud.mark_kb_indexed(db, kb_id)
    return {"success": True, "kb_id": kb_id, "indexed_in_pinecone": indexed}


@app.post("/kb/sync-pinecone")
def sync_kb_to_pinecone(db: Session = Depends(get_db), _role: str = Depends(require_role("admin"))):
    pending = crud.get_kb_docs_unindexed(db)
    succeeded, failed = 0, 0
    for doc in pending:
        if _ingest_kb_doc_safe(doc["id"], doc["title"], doc["doc_type"], doc["content"]):
            crud.mark_kb_indexed(db, doc["id"])
            succeeded += 1
        else:
            failed += 1
    return {"attempted": len(pending), "succeeded": succeeded, "failed": failed}


# ------------------------------- Export ---------------------------------- #
_EXPORTERS = {
    "txt": (export_txt, "text/plain"),
    "docx": (export_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "pdf": (export_pdf, "application/pdf"),
}


@app.get("/export/{rfp_id}")
def export(rfp_id: int, fmt: str = "pdf", db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    fmt = fmt.lower()
    if fmt not in _EXPORTERS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")
    rfp = crud.get_rfp(db, rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    sections = crud.get_draft_sections(db, rfp_id)
    pricing = crud.get_pricing(db, rfp_id)
    fn, media = _EXPORTERS[fmt]
    data = fn(rfp, sections, pricing)
    safe = "".join(ch if ch.isalnum() else "_" for ch in rfp["deal_name"])[:40] or "proposal"
    filename = f"{safe}.{fmt}"

    try:
        export_dir = os.path.join(settings.EXPORTS_DIR, str(rfp_id))
        os.makedirs(export_dir, exist_ok=True)
        timestamp = __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        stored_name = f"{timestamp}_{filename}"
        with open(os.path.join(export_dir, stored_name), "wb") as f:
            f.write(data)
        crud.log_action(db, rfp_id, "Export Stored", "System",
                        f"Saved server copy: {stored_name} ({fmt.upper()}, {len(data)} bytes)")
    except Exception:
        logger.exception("Could not persist export to disk for rfp_id=%s (fmt=%s); "
                         "streaming to client anyway.", rfp_id, fmt)

    return StreamingResponse(
        io.BytesIO(data), media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/export/{rfp_id}/history")
def export_history(rfp_id: int, db: Session = Depends(get_db), _auth: str = Depends(require_api_key)):
    export_dir = os.path.join(settings.EXPORTS_DIR, str(rfp_id))
    if not os.path.isdir(export_dir):
        return {"exports": []}
    files = []
    for name in os.listdir(export_dir):
        path = os.path.join(export_dir, name)
        if os.path.isfile(path):
            files.append({
                "filename": name,
                "size_bytes": os.path.getsize(path),
                "modified_at": __import__("datetime").datetime.utcfromtimestamp(
                    os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
            })
    files.sort(key=lambda f: f["modified_at"], reverse=True)
    return {"exports": files}

@app.get("/evaluation/{rfp_id}/latencies")
async def get_evaluation_latencies(
    rfp_id: int,
    _auth: str = Depends(require_api_key),
):
    trace_id = get_trace_id_for_rfp(rfp_id)

    if not trace_id:
        return {
            "trace_id": None,
            "latencies": {},
        }

    latencies = get_trace_latencies(trace_id)

    return {
        "trace_id": trace_id,
        "latencies": latencies,
    }