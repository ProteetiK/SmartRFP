# ===========================================================================
#  backend/crud.py  — All database operations for SmartRFP
#  BUG FIXES applied:
#  1. use_web_search cast to int(bool) so PostgreSQL integer column accepts it
#  2. EvaluationMetrics (plural) — was wrongly referenced as EvaluationMetric
#  3. crud.log_action now stamps a timestamp so audit rows are complete
#  4. create_rfp returns rfp.id (int) after commit+refresh
# ===========================================================================
from datetime import datetime
from sqlalchemy.orm import Session
from backend import models


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
#  RFP CRUD
# --------------------------------------------------------------------------- #

def create_rfp(
    db: Session,
    deal_name,
    client_name,
    region,
    deadline,
    contact_email,
    notes,
    file_name,
    raw_text,
    assigned_role,
    assigned_to,
    use_web_search,
):
    rfp = models.RFP(
        deal_name=deal_name,
        client_name=client_name,
        region=region,
        deadline=deadline,
        contact_email=contact_email,
        notes=notes,
        file_name=file_name,
        raw_text=raw_text,
        status="Drafting",
        assigned_role=assigned_role,
        assigned_to=assigned_to,
        # FIX: PostgreSQL column is INTEGER — cast Python bool to int
        use_web_search=int(bool(use_web_search)),
        created_at=_now(),
        updated_at=_now(),
    )

    db.add(rfp)
    db.commit()
    db.refresh(rfp)

    # FIX: return the integer id, not the ORM object
    return rfp.id


def get_rfp(db: Session, rfp_id: int):
    return (
        db.query(models.RFP)
        .filter(models.RFP.id == rfp_id)
        .first()
    )


def list_rfps(db: Session):
    return (
        db.query(models.RFP)
        .order_by(models.RFP.id.desc())
        .all()
    )


def update_rfp_metrics(
    db: Session,
    rfp_id: int,
    num_requirements: int,
    num_flags: int,
    status: str,
):
    rfp = get_rfp(db, rfp_id)

    if rfp:
        rfp.num_requirements = num_requirements
        rfp.num_flags = num_flags
        rfp.status = status
        rfp.updated_at = _now()
        db.commit()

def update_rfp_status(
    db: Session,
    rfp_id: int,
    status: str,
):
    rfp = get_rfp(db, rfp_id)

    if rfp:
        rfp.status = status
        rfp.updated_at = _now()
        db.commit()

def delete_rfp(db: Session, rfp_id: int):
    rfp = db.query(models.RFP).filter(models.RFP.id == rfp_id).first()

    if rfp:
        db.delete(rfp)
        db.commit()
          
# --------------------------------------------------------------------------- #
#  Requirements
# --------------------------------------------------------------------------- #

def save_requirements(db: Session, rfp_id: int, requirements: list):
    db.query(models.Requirement).filter(
        models.Requirement.rfp_id == rfp_id
    ).delete()

    for r in requirements:
        db.add(
            models.Requirement(
                rfp_id=rfp_id,
                section=r.get("section", ""),
                text=r.get("text", ""),
            )
        )

    db.commit()


def get_requirements(db: Session, rfp_id: int):
    return (
        db.query(models.Requirement)
        .filter(models.Requirement.rfp_id == rfp_id)
        .all()
    )


# --------------------------------------------------------------------------- #
#  Draft Sections
# --------------------------------------------------------------------------- #

def save_draft_sections(db: Session, rfp_id: int, sections: list):
    db.query(models.DraftSection).filter(
        models.DraftSection.rfp_id == rfp_id
    ).delete()

    for s in sections:
        db.add(
            models.DraftSection(
                rfp_id=rfp_id,
                section_title=s.get("section_title"),
                content=s.get("content"),
                source=s.get("source"),
                flag_type=s.get("flag_type"),
                flag_note=s.get("flag_note"),
                confidence=s.get("confidence"),
            )
        )

    db.commit()


def get_draft_sections(db: Session, rfp_id: int):
    return (
        db.query(models.DraftSection)
        .filter(models.DraftSection.rfp_id == rfp_id)
        .all()
    )

def update_draft_section(db: Session, section_id: int, content: str):
    section = (
        db.query(models.DraftSection)
        .filter(models.DraftSection.id == section_id)
        .first()
    )

    if section:
        section.content = content
        db.commit()


# --------------------------------------------------------------------------- #
#  Pricing
# --------------------------------------------------------------------------- #

def save_pricing(db: Session, rfp_id: int, pricing_items: list):
    db.query(models.Pricing).filter(
        models.Pricing.rfp_id == rfp_id
    ).delete()

    for p in pricing_items:
        db.add(
            models.Pricing(
                rfp_id=rfp_id,
                item=p["item"],
                qty=p["qty"],
                unit_price=p["unit_price"],
                total=p["total"],
                fetched_at=p["fetched_at"],
                source=p["source"],
                # FIX: cast stale bool → int for PostgreSQL INTEGER column
                stale=int(bool(p.get("stale", False))),
            )
        )

    db.commit()


def get_pricing(db: Session, rfp_id: int):
    return (
        db.query(models.Pricing)
        .filter(models.Pricing.rfp_id == rfp_id)
        .all()
    )


# --------------------------------------------------------------------------- #
#  Evaluation Metrics
# --------------------------------------------------------------------------- #

def save_evaluation_metrics(db: Session, rfp_id: int, metrics: dict):
    # FIX: correct class name is EvaluationMetrics (plural)
    db.query(models.EvaluationMetrics).filter(
        models.EvaluationMetrics.rfp_id == rfp_id
    ).delete()

    db.add(
        models.EvaluationMetrics(
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
        )
    )

    db.commit()


def get_evaluation_metrics(db: Session, rfp_id: int):
    return (
        db.query(models.EvaluationMetrics)
        .filter(models.EvaluationMetrics.rfp_id == rfp_id)
        .first()
    )


# --------------------------------------------------------------------------- #
#  Knowledge Base
# --------------------------------------------------------------------------- #

def add_kb_doc(db: Session, title, doc_type, content):
    db.add(
        models.KnowledgeBase(
            title=title,
            doc_type=doc_type,
            content=content,
        )
    )
    db.commit()


def get_kb_docs(db: Session):
    return db.query(models.KnowledgeBase).all()


def kb_count(db: Session):
    return db.query(models.KnowledgeBase).count()


# --------------------------------------------------------------------------- #
#  Audit Log
# --------------------------------------------------------------------------- #

def log_action(db: Session, rfp_id, action, actor, detail=""):
    db.add(
        models.AuditLog(
            rfp_id=rfp_id,
            action=action,
            actor=actor,
            detail=detail,
            timestamp=_now(),
        )
    )
    db.commit()


def get_audit_log(db: Session, rfp_id):
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.rfp_id == rfp_id)
        .order_by(models.AuditLog.id.desc())
        .all()
    )