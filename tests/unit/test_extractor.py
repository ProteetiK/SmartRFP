"""
Unit tests for agents/extractor.py
"""

import json

import pytest

from agents.extractor import (
    extract_requirements,
    _heuristic_extract,
    _llm_extract,
)


# ----------------------------------------------------------------------
# Heuristic extraction
# ----------------------------------------------------------------------

def test_extract_must_requirement():

    text = """
Vendor must encrypt customer data.
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) == 1
    assert "encrypt customer data" in reqs[0]["text"]


def test_extract_shall_requirement():

    text = """
Vendor shall support SSO.
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) == 1
    assert "support SSO" in reqs[0]["text"]


def test_extract_should_requirement():

    text = """
Vendor should provide migration services.
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) == 1


def test_question_is_requirement():

    text = """
How do you perform disaster recovery?
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) == 1
    assert reqs[0]["text"].endswith("?")


# ----------------------------------------------------------------------
# Section detection
# ----------------------------------------------------------------------

def test_section_header_detection():

    text = """
1. Security

Vendor shall support MFA.

2. Migration

Vendor should migrate databases.
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) == 2

    assert reqs[0]["section"] == "1. Security"

    assert reqs[1]["section"] == "2. Migration"


# ----------------------------------------------------------------------
# Fallback mode
# ----------------------------------------------------------------------

def test_fallback_when_no_keywords():

    text = """
This document describes a software project. It contains information regarding
implementation, architecture, deployment, maintenance and operations, but does
not explicitly contain requirement keywords.
"""

    reqs = _heuristic_extract(text)

    assert len(reqs) > 0

    assert reqs[0]["section"].startswith("Section")


def test_max_items_limit():

    text = "\n".join(
        f"Vendor shall complete task {i}."
        for i in range(100)
    )

    reqs = _heuristic_extract(
        text,
        max_items=10,
    )

    assert len(reqs) == 10


# ----------------------------------------------------------------------
# LLM extraction
# ----------------------------------------------------------------------

def test_llm_extract_success(monkeypatch):

    expected = [

        {
            "section": "Security",
            "text": "Vendor shall support MFA."
        },

        {
            "section": "Migration",
            "text": "Vendor should migrate databases."
        }

    ]

    def fake_chat(*args, **kwargs):
        return json.dumps(expected)

    monkeypatch.setattr(
        "agents.extractor.chat",
        fake_chat,
    )

    result = _llm_extract("dummy")

    assert result == expected


def test_llm_extract_json_fence(monkeypatch):

    payload = """
```json
[
    {
        "section":"Security",
        "text":"Vendor shall support MFA."
    }
]
```
"""

