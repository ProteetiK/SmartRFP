"""
Unit tests for agents/rag_agent.py
"""

import pytest
from pathlib import Path
import database
from agents.rag_agent import RAGAgent
from utils.file_handler import extract_text

# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------

def populate_kb():
    """
    Load every knowledge base document from tests/data into SQLite.
    Supports PDF, DOCX and TXT.
    """

    data_dir = Path(__file__).resolve().parents[2] / "sampleRFPs"

    supported = {".txt", ".pdf", ".docx"}

    for file in data_dir.iterdir():

        if file.suffix.lower() not in supported:
            continue

        content = extract_text(
            file.name,
            file.read_bytes(),
        )

        database.add_kb_doc(
            title=file.stem.replace("_", " ").title(),
            doc_type=file.suffix[1:].upper(),
            content=content,
        )
    print(database.kb_count())
    print(database.get_kb_docs())

# --------------------------------------------------------------------
# Initialization
# --------------------------------------------------------------------

def test_empty_database():

    rag = RAGAgent()

    assert rag.docs == []

    results = rag.retrieve("security")

    assert results == []


def test_initialization_loads_documents(temp_db):

    populate_kb()

    rag = RAGAgent()

    assert len(rag.docs) > 0


# --------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------

def test_security_query_returns_security_doc(temp_db):

    populate_kb()
    rag = RAGAgent()

    results = rag.retrieve("security")

    assert len(results) >= 1

    assert results[0]["title"] == "Cloud1 Rfp"


def test_migration_query_returns_migration_doc(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve("migration")

    assert len(results) >= 1

    assert results[0]["title"] == "Sample Kb"


def test_support_query_returns_support_doc(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve("telecom vendor support")

    assert len(results) >= 1

    assert results[0]["title"] == "Rfp 09 Telecom Network"


# --------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------

def test_best_match_is_first(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve(
        "Education",
        top_k=3,
    )

    assert len(results) > 0

    assert results[0]["title"] == "Response Education"


def test_top_k_limit(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve(
        "support migration security",
        top_k=2,
    )

    assert len(results) <= 2


# --------------------------------------------------------------------
# Unknown query
# --------------------------------------------------------------------

def test_unknown_query_returns_empty(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve(
        "banana elephant microwave",
    )

    assert results == []


# --------------------------------------------------------------------
# Returned structure
# --------------------------------------------------------------------

def test_result_schema(temp_db):

    populate_kb()

    rag = RAGAgent()

    result = rag.retrieve(
        "security"
    )[0]

    assert "title" in result
    assert "doc_type" in result
    assert "content" in result
    assert "score" in result


def test_score_is_float(temp_db):

    populate_kb()

    rag = RAGAgent()

    result = rag.retrieve("security")[0]

    assert isinstance(result["score"], float)


def test_score_between_zero_and_one(temp_db):

    populate_kb()

    rag = RAGAgent()

    result = rag.retrieve("security")[0]

    assert 0.0 <= result["score"] <= 1.0


# --------------------------------------------------------------------
# Multiple retrievals
# --------------------------------------------------------------------

def test_multiple_queries_are_independent(temp_db):

    populate_kb()

    rag = RAGAgent()

    sec = rag.retrieve("security")

    mig = rag.retrieve("migration")

    assert sec[0]["title"] != mig[0]["title"]


# --------------------------------------------------------------------
# Similarity threshold
# --------------------------------------------------------------------

def test_similarity_threshold_filters_noise(temp_db):

    populate_kb()

    rag = RAGAgent()

    results = rag.retrieve(
        "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    )

    assert results == []