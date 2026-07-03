"""
Integration tests for the SmartRFP pipeline.

External services (Groq/Tavily) are mocked.
SQLite database is real.
"""

import database

from pipeline import run_pipeline


# ---------------------------------------------------------------------
# Fake components
# ---------------------------------------------------------------------

def fake_requirements(text):

    return [
        {
            "section": "Security",
            "text": "Vendor shall support MFA."
        },
        {
            "section": "Migration",
            "text": "Vendor shall migrate databases."
        }
    ]


class FakeRAG:

    docs = [
        {
            "title": "Security Guide",
            "doc_type": "Guide",
            "content": "Supports MFA."
        }
    ]

    def retrieve(self, query, top_k=3):

        return self.docs

def fake_pricing(*args, **kwargs):
    return (
        [
            {
                "item": "Professional Services",
                "qty": "1",
                "unit_price": 1000,
                "total": 1000,
                "fetched_at": "today",
                "source": "pricing-api",
                "stale": False,
            }
        ],
        None,
    )

def fake_generate(requirements, rag, pricing, web):
    return [
        {
            "section_title": "Executive Summary",
            "content": "Generated content",
            "source": "LLM",
            "flag_type": None,
            "flag_note": None,
            "confidence": "high",
        }
    ]
      
def fake_eval(**kwargs):

    return {

        "proposal_completeness": 1.0,
        "average_confidence": 1.0,
        "context_coverage": 1.0,
        "hallucination_flags": 0,
        "pricing_freshness": 1.0,
        "sections_generated": 1,
        "requirements": 2,
        "runtime_seconds": 0.1,
        "knowledge_documents": 1,
        "pricing_items": 1,
        "llm_calls": 0,
        "demo_mode": True,

        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "context_recall": None,

        "mrr": 1.0,
        "hit_rate": 1.0,
        "chunk_overlap": 0.0,

    }


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_pipeline_success(monkeypatch, temp_db):

    monkeypatch.setattr(
        "pipeline.extract_requirements",
        fake_requirements,
    )

    monkeypatch.setattr(
        "pipeline.RAGAgent",
        FakeRAG,
    )

    monkeypatch.setattr(
        "pipeline.fetch_pricing",
        fake_pricing,
    )

    monkeypatch.setattr(
        "pipeline.generate_draft",
        fake_generate,
    )

    monkeypatch.setattr(
        "pipeline.evaluate_pipeline",
        fake_eval,
    )

    rfp = database.create_rfp(
        deal_name="Deal",
        client_name="Client",
        region="UK",
        deadline="Tomorrow",
        contact_email="a@b.com",
        notes="",
        file_name="rfp.txt",
        raw_text="Vendor shall support MFA.",
        assigned_role="Reviewer",
        assigned_to="Alice",
        use_web_search=False,
    )

    result = run_pipeline(
        rfp,
        "Vendor shall support MFA.",
        use_web_search=False,
    )

    assert result["requirements"] == 2

    assert result["sections"] == 1

    assert result["flags"] == 0


def test_pipeline_saves_requirements(monkeypatch, temp_db):

    monkeypatch.setattr(
        "pipeline.extract_requirements",
        fake_requirements,
    )

    monkeypatch.setattr(
        "pipeline.RAGAgent",
        FakeRAG,
    )

    monkeypatch.setattr(
        "pipeline.fetch_pricing",
        fake_pricing,
    )

    monkeypatch.setattr(
        "pipeline.generate_draft",
        fake_generate,
    )

    monkeypatch.setattr(
        "pipeline.evaluate_pipeline",
        fake_eval,
    )

    rfp = database.create_rfp(
        "Deal",
        "Client",
        "",
        "",
        "",
        "",
        "rfp.txt",
        "Vendor shall support MFA.",
        "",
        "",
        False,
    )

    run_pipeline(
        rfp,
        "Vendor shall support MFA.",
    )

    reqs = database.get_requirements(rfp)

    assert len(reqs) == 2


def test_pipeline_saves_sections(monkeypatch, temp_db):

    monkeypatch.setattr(
        "pipeline.extract_requirements",
        fake_requirements,
    )

    monkeypatch.setattr(
        "pipeline.RAGAgent",
        FakeRAG,
    )

    monkeypatch.setattr(
        "pipeline.fetch_pricing",
        fake_pricing,
    )

    monkeypatch.setattr(
        "pipeline.generate_draft",
        fake_generate,
    )

    monkeypatch.setattr(
        "pipeline.evaluate_pipeline",
        fake_eval,
    )

    rfp = database.create_rfp(
        "Deal",
        "Client",
        "",
        "",
        "",
        "",
        "rfp.txt",
        "Vendor shall support MFA.",
        "",
        "",
        False,
    )

    run_pipeline(
        rfp,
        "Vendor shall support MFA.",
    )

    sections = database.get_draft_sections(rfp)

    assert len(sections) == 1


def test_pipeline_saves_pricing(monkeypatch, temp_db):

    monkeypatch.setattr(
        "pipeline.extract_requirements",
        fake_requirements,
    )

    monkeypatch.setattr(
        "pipeline.RAGAgent",
        FakeRAG,
    )

    monkeypatch.setattr(
        "pipeline.fetch_pricing",
        fake_pricing,
    )

    monkeypatch.setattr(
        "pipeline.generate_draft",
        fake_generate,
    )

    monkeypatch.setattr(
        "pipeline.evaluate_pipeline",
        fake_eval,
    )

    rfp = database.create_rfp(
        "Deal",
        "Client",
        "",
        "",
        "",
        "",
        "rfp.txt",
        "Vendor shall support MFA.",
        "",
        "",
        False,
    )

    run_pipeline(
        rfp,
        "Vendor shall support MFA.",
    )

    pricing = database.get_pricing(rfp)

    assert len(pricing) == 1


def test_pipeline_updates_status(monkeypatch, temp_db):

    monkeypatch.setattr(
        "pipeline.extract_requirements",
        fake_requirements,
    )

    monkeypatch.setattr(
        "pipeline.RAGAgent",
        FakeRAG,
    )

    monkeypatch.setattr(
        "pipeline.fetch_pricing",
        fake_pricing,
    )

    monkeypatch.setattr(
        "pipeline.generate_draft",
        fake_generate,
    )

    monkeypatch.setattr(
        "pipeline.evaluate_pipeline",
        fake_eval,
    )

    rfp = database.create_rfp(
        "Deal",
        "Client",
        "",
        "",
        "",
        "",
        "rfp.txt",
        "Vendor shall support MFA.",
        "",
        "",
        False,
    )

    run_pipeline(
        rfp,
        "Vendor shall support MFA.",
    )

    row = database.get_rfp(rfp)

    assert row["status"] == "In Review"