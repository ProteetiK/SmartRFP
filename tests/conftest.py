"""
Shared fixtures for SmartRFP tests.

Run:
    pytest

These fixtures ensure:

- Every test uses a temporary SQLite database.
- No production database is touched.
- Sample KB documents exist.
- Sample RFP text is available.
- No real Groq/Tavily calls occur unless explicitly requested.
"""

import pytest
from pathlib import Path
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import database


# --------------------------------------------------------------------
# Temporary database
# --------------------------------------------------------------------

@pytest.fixture(scope="function")
def temp_db(tmp_path_factory, monkeypatch):
    """
    Create an isolated SQLite database for all tests.
    """

    db_dir = tmp_path_factory.mktemp("db")

    db_path = db_dir / "test_smartrfp.db"

    monkeypatch.setattr(config, "DB_PATH", str(db_path))

    database.init_db()

    yield db_path


# --------------------------------------------------------------------
# Clean database before every test
# --------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_database(temp_db):
    """
    Empty every table before each test.
    """

    conn = database.get_conn()

    cur = conn.cursor()

    tables = [
        "rfps",
        "requirements",
        "draft_sections",
        "pricing",
        "knowledge_base",
        "audit_log",
        "evaluation_metrics",
    ]

    for table in tables:
        cur.execute(f"DELETE FROM {table}")

    conn.commit()
    conn.close()


# --------------------------------------------------------------------
# Sample RFP
# --------------------------------------------------------------------

@pytest.fixture
def sample_rfp():

    return """
1. Security

The vendor shall support SSO.

The vendor must encrypt all customer data.

2. Migration

The vendor should provide migration services.

3. Support

Please describe your managed support offering.

4. Pricing

Provide pricing for implementation and licences.
"""


# --------------------------------------------------------------------
# Sample requirements
# --------------------------------------------------------------------

@pytest.fixture
def sample_requirements():

    return [
        {
            "section": "Security",
            "text": "Vendor shall support SSO."
        },
        {
            "section": "Migration",
            "text": "Vendor should provide migration services."
        }
    ]


# --------------------------------------------------------------------
# Sample KB
# --------------------------------------------------------------------

@pytest.fixture
def sample_kb():

    docs = [

        {
            "title": "Security Guide",
            "doc_type": "Policy",
            "content":
                "Our platform supports SSO, MFA, encryption at rest, RBAC and audit logging."
        },

        {
            "title": "Migration Playbook",
            "doc_type": "Guide",
            "content":
                "Migration follows assessment, planning, execution and validation."
        },

        {
            "title": "Support Handbook",
            "doc_type": "Process",
            "content":
                "Managed support is available 24x7 with incident response."
        }

    ]

    for d in docs:
        database.add_kb_doc(
            d["title"],
            d["doc_type"],
            d["content"],
        )

    return docs


# --------------------------------------------------------------------
# Sample pricing
# --------------------------------------------------------------------

@pytest.fixture
def sample_pricing():

    return [

        {
            "item": "Security Hardening Package",
            "qty": "1",
            "unit_price": 38500,
            "total": 38500,
            "fetched_at": "01 Jan 2025",
            "source": "pricing-api",
            "stale": False,
        },

        {
            "item": "Margin (18%)",
            "qty": "-",
            "unit_price": 6930,
            "total": 6930,
            "fetched_at": "01 Jan 2025",
            "source": "pricing-api",
            "stale": False,
        }

    ]


# --------------------------------------------------------------------
# Sample draft sections
# --------------------------------------------------------------------

@pytest.fixture
def sample_sections():

    return [

        {
            "section_title": "Executive Summary",
            "content": "This is a proposal.",
            "source": "System",
            "flag_type": None,
            "flag_note": None,
            "confidence": "high",
        },

        {
            "section_title": "Pricing",
            "content": "Estimated cost is $45,000.",
            "source": "Pricing Agent",
            "flag_type": None,
            "flag_note": None,
            "confidence": "high",
        }

    ]


# --------------------------------------------------------------------
# Disable Groq
# --------------------------------------------------------------------

@pytest.fixture
def disable_llm(monkeypatch):
    """
    Force demo mode.
    """

    monkeypatch.setattr(config, "GROQ_API_KEY", "")


# --------------------------------------------------------------------
# Fake chat() implementation
# --------------------------------------------------------------------

@pytest.fixture
def fake_chat(monkeypatch):

    import llm

    def _fake_chat(*args, **kwargs):
        return "Mock LLM response."

    monkeypatch.setattr(
        llm,
        "chat",
        _fake_chat,
    )


# --------------------------------------------------------------------
# Disable Tavily
# --------------------------------------------------------------------

@pytest.fixture
def disable_web(monkeypatch):

    monkeypatch.delenv(
        "TAVILY_API_KEY",
        raising=False,
    )