from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class RFP(Base):
    __tablename__ = "rfps"

    id = Column(Integer, primary_key=True, index=True)
    deal_name = Column(String, nullable=False)
    client_name = Column(String)
    region = Column(String)
    deadline = Column(String)
    contact_email = Column(String)
    notes = Column(Text)
    file_name = Column(String)
    raw_text = Column(Text)
    status = Column(String, default="Uploaded")
    assigned_role = Column(String)
    assigned_to = Column(String)
    num_requirements = Column(Integer, default=0)
    num_flags = Column(Integer, default=0)
    use_web_search = Column(Integer, default=1)
    error_message = Column(Text)  
    created_at = Column(String)
    updated_at = Column(String)

    requirements = relationship("Requirement", back_populates="rfp", cascade="all, delete-orphan")
    draft_sections = relationship("DraftSection", back_populates="rfp", cascade="all, delete-orphan")
    pricing = relationship("Pricing", back_populates="rfp", cascade="all, delete-orphan")
    evaluations = relationship("EvaluationMetrics", back_populates="rfp", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="rfp", cascade="all, delete-orphan")


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    section = Column(String)
    text = Column(Text)
    rfp = relationship("RFP", back_populates="requirements")


class DraftSection(Base):
    __tablename__ = "draft_sections"
    id = Column(Integer, primary_key=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    section_title = Column(String)
    content = Column(Text)
    source = Column(Text)
    flag_type = Column(String)
    flag_note = Column(Text)
    confidence = Column(String)
    rfp = relationship("RFP", back_populates="draft_sections")


class Pricing(Base):
    __tablename__ = "pricing"
    id = Column(Integer, primary_key=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    item = Column(String)
    qty = Column(String)
    unit_price = Column(Float)
    total = Column(Float)
    fetched_at = Column(String)
    source = Column(String)
    stale = Column(Integer, default=0)
    rfp = relationship("RFP", back_populates="pricing")


class EvaluationMetrics(Base):
    __tablename__ = "evaluation_metrics"
    id = Column(Integer, primary_key=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    proposal_completeness = Column(Float)
    average_confidence = Column(Float)
    context_coverage = Column(Float)
    hallucination_flags = Column(Integer)
    pricing_freshness = Column(Float)
    sections_generated = Column(Integer)
    requirements_extracted = Column(Integer)
    runtime_seconds = Column(Float)
    knowledge_documents = Column(Integer)
    retrieved_docs_count = Column(Integer, nullable=True, default=0)
    pricing_items = Column(Integer)
    llm_calls = Column(Integer)
    demo_mode = Column(Integer)
    faithfulness = Column(Float)
    answer_relevancy = Column(Float)
    context_precision = Column(Float)
    context_recall = Column(Float)
    mrr = Column(Float)
    hit_rate = Column(Float)
    chunk_overlap = Column(Float)
    evaluated_at = Column(String)
    ragas_faithfulness = Column(Float, nullable=True)
    ragas_answer_relevancy = Column(Float, nullable=True)
    ragas_context_precision = Column(Float, nullable=True)
    ragas_context_recall = Column(Float, nullable=True)
    ragas_evaluated_at = Column(String, nullable=True)
    ragas_status = Column(String, nullable=True, default="pending")  # pending|running|completed|failed|skipped
    ragas_error = Column(String, nullable=True)
    ragas_attempts = Column(Integer, nullable=True, default=0)
    below_threshold = Column(Integer, nullable=True, default=0)
    threshold_notes = Column(String, nullable=True)
    stage_latencies_json = Column(String, nullable=True)
    rfp = relationship("RFP", back_populates="evaluations")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    doc_type = Column(String)
    content = Column(Text)
    pinecone_indexed = Column(Integer, nullable=True, default=0)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    action = Column(String)
    actor = Column(String)
    detail = Column(Text)
    timestamp = Column(String)
    rfp = relationship("RFP", back_populates="audit_logs")


class ResourceRate(Base):
    __tablename__ = "resource_rates"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(100), nullable=False)
    experience_level = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    monthly_rate = Column(Numeric(12, 2), nullable=False)
    hourly_rate = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="INR")
    active = Column(Boolean, default=True)
    effective_from = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())