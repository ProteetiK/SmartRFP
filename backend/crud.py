from datetime import datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend import models


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _to_dict(obj):
    if obj is None:
        return None
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


# --------------------------------------------------------------------------- #
#  RFP
# --------------------------------------------------------------------------- #
def create_rfp(db: Session, deal_name, client_name, region, deadline, contact_email,
               notes, file_name, raw_text, assigned_role, assigned_to, use_web_search):
    rfp = models.RFP(
        deal_name=deal_name, client_name=client_name, region=region, deadline=deadline,
        contact_email=contact_email, notes=notes, file_name=file_name, raw_text=raw_text,
        status="Drafting", assigned_role=assigned_role, assigned_to=assigned_to,
        use_web_search=int(bool(use_web_search)), created_at=_now(), updated_at=_now(),
    )
    db.add(rfp)
    db.commit()
    db.refresh(rfp)
    return rfp.id


def get_rfp(db: Session, rfp_id: int):
    return _to_dict(db.query(models.RFP).get(rfp_id))


def get_rfp_obj(db: Session, rfp_id: int):
    """Return the ORM object (used internally by services that need raw_text)."""
    return db.query(models.RFP).get(rfp_id)


def list_rfps(db: Session):
    rows = db.query(models.RFP).order_by(models.RFP.id.desc()).all()
    return [_to_dict(r) for r in rows]


def update_rfp_metrics(db: Session, rfp_id, num_requirements, num_flags, status):
    rfp = db.query(models.RFP).get(rfp_id)
    if rfp:
        rfp.num_requirements = num_requirements
        rfp.num_flags = num_flags
        rfp.status = status
        rfp.updated_at = _now()
        db.commit()


def update_rfp_status(db: Session, rfp_id, status):
    rfp = db.query(models.RFP).get(rfp_id)
    if rfp:
        rfp.status = status
        rfp.updated_at = _now()
        db.commit()


def set_rfp_error(db: Session, rfp_id, message):
    rfp = db.query(models.RFP).get(rfp_id)
    if rfp:
        rfp.status = "Failed"
        rfp.error_message = (message or "")[:2000]
        rfp.updated_at = _now()
        db.commit()


def update_rfp_assignment(db: Session, rfp_id, assigned_role, assigned_to):
    rfp = db.query(models.RFP).get(rfp_id)
    if rfp:
        rfp.assigned_role = assigned_role
        rfp.assigned_to = assigned_to
        db.commit()


def delete_rfp(db: Session, rfp_id):
    rfp = db.query(models.RFP).get(rfp_id)
    if rfp:
        db.delete(rfp)   # cascade removes children
        db.commit()


# --------------------------------------------------------------------------- #
#  Requirements
# --------------------------------------------------------------------------- #
def save_requirements(db: Session, rfp_id, requirements):
    db.query(models.Requirement).filter(models.Requirement.rfp_id == rfp_id).delete()
    for r in requirements:
        db.add(models.Requirement(rfp_id=rfp_id, section=r.get("section", ""), text=r.get("text", "")))
    db.commit()


def get_requirements(db: Session, rfp_id):
    rows = db.query(models.Requirement).filter(models.Requirement.rfp_id == rfp_id).all()
    return [_to_dict(r) for r in rows]


# --------------------------------------------------------------------------- #
#  Draft sections
# --------------------------------------------------------------------------- #
def save_draft_sections(db: Session, rfp_id, sections):
    db.query(models.DraftSection).filter(models.DraftSection.rfp_id == rfp_id).delete()
    for s in sections:
        db.add(models.DraftSection(
            rfp_id=rfp_id, section_title=s.get("section_title"), content=s.get("content"),
            source=s.get("source"), flag_type=s.get("flag_type"),
            flag_note=s.get("flag_note"), confidence=s.get("confidence"),
        ))
    db.commit()


def get_draft_sections(db: Session, rfp_id):
    rows = db.query(models.DraftSection).filter(models.DraftSection.rfp_id == rfp_id).all()
    return [_to_dict(r) for r in rows]


def update_draft_section(db: Session, section_id, content):
    row = db.query(models.DraftSection).get(section_id)
    if row:
        row.content = content
        db.commit()


# --------------------------------------------------------------------------- #
#  Pricing
# --------------------------------------------------------------------------- #
def save_pricing(db: Session, rfp_id, items):
    db.query(models.Pricing).filter(models.Pricing.rfp_id == rfp_id).delete()
    for p in items:
        db.add(models.Pricing(
            rfp_id=rfp_id, item=p["item"], qty=str(p.get("qty", "1")),
            unit_price=float(p.get("unit_price", 0)), total=float(p.get("total", 0)),
            fetched_at=p.get("fetched_at", ""), source=p.get("source", ""),
            stale=int(bool(p.get("stale", False))),
        ))
    db.commit()


def get_pricing(db: Session, rfp_id):
    rows = db.query(models.Pricing).filter(models.Pricing.rfp_id == rfp_id).all()
    return [_to_dict(r) for r in rows]


# --------------------------------------------------------------------------- #
#  Evaluation metrics
# --------------------------------------------------------------------------- #
def save_evaluation_metrics(db: Session, rfp_id, metrics):
    import json as _json
    db.query(models.EvaluationMetrics).filter(models.EvaluationMetrics.rfp_id == rfp_id).delete()
    stage_latencies = metrics.get("stage_latencies") or {}
    db.add(models.EvaluationMetrics(
        rfp_id=rfp_id,
        proposal_completeness=metrics.get("proposal_completeness", 0),
        average_confidence=metrics.get("average_confidence", 0),
        context_coverage=metrics.get("context_coverage", 0),
        hallucination_flags=metrics.get("hallucination_flags", 0),
        pricing_freshness=metrics.get("pricing_freshness", 0),
        sections_generated=metrics.get("sections_generated", 0),
        requirements_extracted=metrics.get("requirements", 0),
        runtime_seconds=metrics.get("runtime_seconds", 0),
        knowledge_documents=metrics.get("knowledge_documents", 0),
        retrieved_docs_count=metrics.get("retrieved_docs_count", 0),
        pricing_items=metrics.get("pricing_items", 0),
        llm_calls=metrics.get("llm_calls", 0),
        demo_mode=int(bool(metrics.get("demo_mode", False))),
        faithfulness=metrics.get("faithfulness", 0),
        answer_relevancy=metrics.get("answer_relevancy", 0),
        context_precision=metrics.get("context_precision", 0),
        context_recall=metrics.get("context_recall", 0),
        mrr=metrics.get("mrr", 0),
        hit_rate=metrics.get("hit_rate", 0),
        chunk_overlap=metrics.get("chunk_overlap", 0),
        evaluated_at=_now(),
        ragas_status="pending",
        ragas_attempts=0,
        below_threshold=int(bool(metrics.get("below_threshold", False))),
        threshold_notes=metrics.get("threshold_notes"),
        stage_latencies_json=_json.dumps(stage_latencies) if stage_latencies else None,
    ))
    db.commit()


def get_evaluation_metrics(db: Session, rfp_id):
    import json as _json
    d = _to_dict(
        db.query(models.EvaluationMetrics)
        .filter(models.EvaluationMetrics.rfp_id == rfp_id).first()
    )
    if d and d.get("stage_latencies_json"):
        try:
            d["stage_latencies"] = _json.loads(d["stage_latencies_json"])
        except Exception:
            d["stage_latencies"] = {}
    elif d:
        d["stage_latencies"] = {}
    return d


def update_evaluation_metrics(db: Session, rfp_id, patch: dict):
    row = (db.query(models.EvaluationMetrics)
           .filter(models.EvaluationMetrics.rfp_id == rfp_id).first())
    if not row:
        return
    for key, value in patch.items():
        if hasattr(row, key):
            setattr(row, key, value)
    row.ragas_evaluated_at = _now()
    db.commit()


def set_ragas_status(db: Session, rfp_id, status: str, error: str = None, attempts: int = None):
    row = (db.query(models.EvaluationMetrics)
           .filter(models.EvaluationMetrics.rfp_id == rfp_id).first())
    if not row:
        return
    row.ragas_status = status
    if error is not None:
        row.ragas_error = error[:500]
    if attempts is not None:
        row.ragas_attempts = attempts
    db.commit()


def flag_below_threshold(db: Session, rfp_id, notes: str):
    row = (db.query(models.EvaluationMetrics)
           .filter(models.EvaluationMetrics.rfp_id == rfp_id).first())
    if not row:
        return
    row.below_threshold = 1
    row.threshold_notes = notes[:500]
    db.commit()


# --------------------------------------------------------------------------- #
#  Knowledge base
# --------------------------------------------------------------------------- #
def add_kb_doc(db: Session, title, doc_type, content):
    doc = models.KnowledgeBase(title=title, doc_type=doc_type, content=content, pinecone_indexed=0)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc.id


def get_kb_docs(db: Session):
    return [_to_dict(r) for r in db.query(models.KnowledgeBase).all()]


def get_kb_docs_unindexed(db: Session):
    rows = db.query(models.KnowledgeBase).filter(
        (models.KnowledgeBase.pinecone_indexed == 0) | (models.KnowledgeBase.pinecone_indexed.is_(None))
    ).all()
    return [_to_dict(r) for r in rows]


def mark_kb_indexed(db: Session, kb_id: int):
    row = db.query(models.KnowledgeBase).get(kb_id)
    if row:
        row.pinecone_indexed = 1
        db.commit()


def kb_count(db: Session):
    return db.query(models.KnowledgeBase).count()


# --------------------------------------------------------------------------- #
#  Audit log
# --------------------------------------------------------------------------- #
def log_action(db: Session, rfp_id, action, actor, detail=""):
    db.add(models.AuditLog(rfp_id=rfp_id, action=action, actor=actor,
                           detail=detail, timestamp=_now()))
    db.commit()


def get_audit_log(db: Session, rfp_id):
    rows = (db.query(models.AuditLog).filter(models.AuditLog.rfp_id == rfp_id)
            .order_by(models.AuditLog.id.desc()).all())
    return [_to_dict(r) for r in rows]