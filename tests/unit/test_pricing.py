"""
Unit tests for agents/pricing_agent.py
"""

import os
from datetime import datetime

import pytest

from agents.pricing_agent import (
    fetch_pricing,
    _mock_pricing,
    _keywords_in,
)


# --------------------------------------------------------------------
# Keyword detection
# --------------------------------------------------------------------

def test_detect_single_keyword():

    keys = _keywords_in(
        "The project requires cloud infrastructure."
    )

    assert keys == ["cloud"]


def test_detect_multiple_keywords():

    keys = _keywords_in(
        "Cloud migration with managed support and security."
    )

    assert "cloud" in keys
    assert "migration" in keys
    assert "support" in keys
    assert "security" in keys


def test_no_keywords():

    keys = _keywords_in(
        "Completely unrelated sentence."
    )

    assert keys == []


# --------------------------------------------------------------------
# Pricing generation
# --------------------------------------------------------------------

def test_default_pricing_line():

    lines = _mock_pricing(
        1,
        "Random unrelated document."
    )

    assert len(lines) >= 2

    assert lines[0]["item"] == "Professional Services (est.)"


def test_cloud_pricing_generated():

    lines = _mock_pricing(
        1,
        "Cloud migration project."
    )

    items = [l["item"] for l in lines]

    assert any("Cloud" in item or "Compute" in item for item in items)


def test_margin_line_exists():

    lines = _mock_pricing(
        1,
        "Cloud migration."
    )

    assert lines[-1]["item"] == "Margin (18%)"


def test_margin_not_stale():

    lines = _mock_pricing(
        1,
        "Cloud migration."
    )

    assert lines[-1]["stale"] is False


# --------------------------------------------------------------------
# Stale pricing
# --------------------------------------------------------------------

def test_one_stale_line_when_multiple_items():

    lines = _mock_pricing(
        1,
        "Cloud migration support security"
    )

    stale = [l for l in lines if l["stale"]]

    assert len(stale) == 1


def test_default_line_not_stale():

    lines = _mock_pricing(
        1,
        "Nothing relevant."
    )

    assert lines[0]["stale"] is False


# --------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------

def test_pricing_schema():

    line = _mock_pricing(
        1,
        "Cloud"
    )[0]

    expected = {
        "item",
        "qty",
        "unit_price",
        "total",
        "fetched_at",
        "source",
        "stale",
    }

    assert expected.issubset(line.keys())


def test_total_is_numeric():

    line = _mock_pricing(
        1,
        "Cloud"
    )[0]

    assert isinstance(line["total"], float)


def test_source_is_pricing_api():

    line = _mock_pricing(
        1,
        "Cloud"
    )[0]

    assert line["source"] == "pricing-api"


# --------------------------------------------------------------------
# fetch_pricing()
# --------------------------------------------------------------------

def test_fetch_pricing_without_web(monkeypatch):

    monkeypatch.delenv(
        "TAVILY_API_KEY",
        raising=False,
    )

    lines, insight = fetch_pricing(
        1,
        "Cloud migration"
    )

    assert len(lines) > 0

    assert insight is None


def test_fetch_pricing_with_mocked_web(monkeypatch):

    monkeypatch.setattr(
        "agents.pricing_agent._optional_web_insight",
        lambda x: "Latest market pricing"
    )

    lines, insight = fetch_pricing(
        1,
        "Cloud migration"
    )

    assert len(lines) > 0

    assert insight == "Latest market pricing"


# --------------------------------------------------------------------
# Totals
# --------------------------------------------------------------------

def test_margin_is_18_percent():

    lines = _mock_pricing(
        1,
        "Cloud migration"
    )

    subtotal = sum(
        l["total"]
        for l in lines
        if l["item"] != "Margin (18%)"
        and not l["stale"]
    )

    margin = lines[-1]["total"]

    expected = round(subtotal * 0.18, 2)

    assert margin == expected


def test_totals_are_positive():

    lines = _mock_pricing(
        1,
        "Cloud migration security support"
    )

    for line in lines:
        assert line["total"] >= 0