import os
import random
from datetime import datetime, timedelta
from langsmith import trace
from langsmith.run_helpers import get_current_run_tree

from backend.metrics import (
    PRICING_REQUESTS,
    PRICING_ITEMS,
)

RATE_CARD = {
    "cloud":      ("Compute / Cloud SKU (x12)", 12, 17833.0, "pricing-api"),
    "migration":  ("Migration Labor (480 hrs)", 480, 400.0, "pricing-api"),
    "security":   ("Security Hardening Package", 1, 38500.0, "pricing-api"),
    "support":    ("Managed Support (12 mo)", 12, 4200.0, "pricing-api"),
    "data":       ("Data Platform Setup", 1, 64000.0, "pricing-api"),
    "license":    ("Software Licenses (annual)", 1, 52000.0, "pricing-api"),
}
DEFAULT_LINE = ("Professional Services (est.)", 1, 45000.0, "pricing-api")


def _keywords_in(text: str):
    t = (text or "").lower()
    return [k for k in RATE_CARD if k in t]

def _mock_pricing(rfp_id: int, rfp_text: str):
    now = datetime.now()
    keys = _keywords_in(rfp_text) or []
    lines = []

    chosen = keys[:4] if keys else []
    if not chosen:
        item, qty, unit, src = DEFAULT_LINE
        lines.append(_line(item, qty, unit, src, now, stale=False))
    else:
        for i, k in enumerate(chosen):
            item, qty, unit, src = RATE_CARD[k]
            # Deterministically mark ONE line as stale to demonstrate the flag
            stale = (i == len(chosen) - 1 and len(chosen) >= 2)
            lines.append(_line(item, qty, unit, src, now, stale=stale))

    subtotal = sum(l["total"] for l in lines if not l["stale"])
    margin = round(subtotal * 0.18, 2)
    lines.append(_line("Margin (18%)", "-", margin, "pricing-api", now, stale=False,
                       precomputed_total=margin))
    return lines


def _line(item, qty, unit_price, source, now, stale=False, precomputed_total=None):
    if stale:
        fetched = (now - timedelta(days=95)).strftime("%d %b %Y")  # last quarter
    else:
        fetched = now.strftime("%d %b %Y")
    qty_num = qty if isinstance(qty, (int, float)) else 1
    total = precomputed_total if precomputed_total is not None else round(unit_price * qty_num, 2)
    return {
        "item": item,
        "qty": str(qty),
        "unit_price": float(unit_price),
        "total": float(total),
        "fetched_at": fetched,
        "source": source,
        "stale": bool(stale),
    }

def _optional_web_insight(rfp_text: str):
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        # very small query derived from the doc
        topic = " ".join(rfp_text.split()[:8])
        res = client.search(query=f"latest pricing trends {topic}", max_results=2)
        snippets = [r.get("content", "")[:200] for r in res.get("results", [])]
        return " | ".join(s for s in snippets if s)[:400] or None
    except Exception as e:
        print(f"[pricing] Tavily web insight failed: {e}")
        return None

def fetch_pricing(rfp_id: int, rfp_text: str, parent_run=None):
    with trace(
        "Pricing Engine",
        run_type="chain",
        parent=parent_run,
    ):
        PRICING_REQUESTS.inc()
        lines = _mock_pricing(rfp_id, rfp_text)
        insight = _optional_web_insight(rfp_text)
        PRICING_ITEMS.observe(len(lines))
        return lines, insight
