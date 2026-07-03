"""
Unit tests for database.py
"""

import database


# ---------------------------------------------------------------------
# RFP CRUD
# ---------------------------------------------------------------------

def test_create_and_get_rfp(temp_db):

    rfp_id = database.create_rfp(
        deal_name="Cloud Migration",
        client_name="ABC Corp",
        region="APAC",
        deadline="2025-12-31",
        contact_email="abc@test.com",
        notes="Important deal",
        file_name="rfp.pdf",
        raw_text="Sample RFP",
        assigned_role="Reviewer",
        assigned_to="Alice",
        use_web_search=True,
    )

    rfp = database.get_rfp(rfp_id)

    assert rfp is not None
    assert rfp["deal_name"] == "Cloud Migration"
    assert rfp["client_name"] == "ABC Corp"
    assert rfp["assigned_to"] == "Alice"


def test_list_rfps_returns_created_rfps(temp_db):

    database.create_rfp(
        "Deal1",
        "Client1",
        "US",
        "",
        "",
        "",
        "a.pdf",
        "text",
        "",
        "",
        True,
    )

    database.create_rfp(
        "Deal2",
        "Client2",
        "UK",
        "",
        "",
        "",
        "b.pdf",
        "text",
        "",
        "",
        True,
    )

    rfps = database.list_rfps()

    assert len(rfps) == 2


def test_update_rfp_status(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "a.pdf",
        "text",
        "",
        "",
        True,
    )

    database.update_rfp_status(
        rfp_id,
        "Completed",
    )

    rfp = database.get_rfp(rfp_id)

    assert rfp["status"] == "Completed"


def test_update_rfp_assignment(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "a.pdf",
        "text",
        "",
        "",
        True,
    )

    database.update_rfp_assignment(
        rfp_id,
        "SME",
        "Bob",
    )

    rfp = database.get_rfp(rfp_id)

    assert rfp["assigned_role"] == "SME"
    assert rfp["assigned_to"] == "Bob"


def test_update_metrics(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "a.pdf",
        "text",
        "",
        "",
        True,
    )

    database.update_rfp_metrics(
        rfp_id,
        num_requirements=12,
        num_flags=3,
        status="In Review",
    )

    rfp = database.get_rfp(rfp_id)

    assert rfp["num_requirements"] == 12
    assert rfp["num_flags"] == 3
    assert rfp["status"] == "In Review"


# ---------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------

def test_save_and_get_requirements(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    reqs = [

        {
            "section": "Security",
            "text": "Vendor shall support MFA."
        },

        {
            "section": "Migration",
            "text": "Vendor should migrate databases."
        }

    ]

    database.save_requirements(
        rfp_id,
        reqs,
    )

    result = database.get_requirements(rfp_id)

    assert len(result) == 2
    assert result[0]["section"] == "Security"


# ---------------------------------------------------------------------
# Draft sections
# ---------------------------------------------------------------------

def test_save_and_get_draft_sections(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    sections = [

        {
            "section_title": "Executive Summary",
            "content": "Proposal",
            "source": "LLM",
            "flag_type": None,
            "flag_note": None,
            "confidence": "high",
        }

    ]

    database.save_draft_sections(
        rfp_id,
        sections,
    )

    result = database.get_draft_sections(rfp_id)

    assert len(result) == 1
    assert result[0]["section_title"] == "Executive Summary"


def test_update_draft_section(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    database.save_draft_sections(
        rfp_id,
        [
            {
                "section_title": "Executive Summary",
                "content": "Old",
                "source": "LLM",
                "flag_type": None,
                "flag_note": None,
                "confidence": "high",
            }
        ],
    )

    section = database.get_draft_sections(rfp_id)[0]

    database.update_draft_section(
        section["id"],
        "New Content",
    )

    updated = database.get_draft_sections(rfp_id)[0]

    assert updated["content"] == "New Content"


# ---------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------

def test_save_and_get_pricing(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    pricing = [

        {
            "item": "Cloud",
            "qty": "1",
            "unit_price": 1000,
            "total": 1000,
            "fetched_at": "Today",
            "source": "pricing-api",
            "stale": False,
        }

    ]

    database.save_pricing(
        rfp_id,
        pricing,
    )

    result = database.get_pricing(rfp_id)

    assert len(result) == 1
    assert result[0]["item"] == "Cloud"


# ---------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------

def test_add_and_get_kb_docs(temp_db):

    database.add_kb_doc(
        "Security Guide",
        "Policy",
        "Supports SSO.",
    )

    docs = database.get_kb_docs()

    assert len(docs) == 1
    assert docs[0]["title"] == "Security Guide"


def test_kb_count(temp_db):

    database.add_kb_doc(
        "A",
        "Guide",
        "Content",
    )

    database.add_kb_doc(
        "B",
        "Guide",
        "Content",
    )

    assert database.kb_count() == 2


# ---------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------

def test_log_action(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    database.log_action(
        rfp_id,
        "Generated",
        "System",
        "Draft created",
    )

    logs = database.get_audit_log(rfp_id)

    assert len(logs) == 1
    assert logs[0]["action"] == "Generated"


# ---------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------

def test_delete_rfp_cascades(temp_db):

    rfp_id = database.create_rfp(
        "Deal",
        "",
        "",
        "",
        "",
        "",
        "file",
        "text",
        "",
        "",
        True,
    )

    database.save_requirements(
        rfp_id,
        [
            {
                "section": "A",
                "text": "B",
            }
        ],
    )

    database.log_action(
        rfp_id,
        "Action",
        "System",
    )

    database.delete_rfp(rfp_id)

    assert database.get_rfp(rfp_id) is None
    assert database.get_requirements(rfp_id) == []
    assert database.get_audit_log(rfp_id) == []