import streamlit as st
from datetime import date
import database as db
from ui.ui_utils import (topbar, go)
from config import (SUPPORTED_TYPES, MAX_UPLOAD_MB, REVIEWER_ROLES)
from utils.file_handler import extract_text
from .api import upload_rfp
import state
import os
import requests
# =========================================================================== #
#  PAGE: Upload
# =========================================================================== #
def page_upload():
    ss = state.get_state()
    topbar("Upload RFP Document", "Upload your RFP document and let AI analyze it for you.", "☁️")
    up = st.file_uploader("Drag & drop your file here", type=SUPPORTED_TYPES,
                          label_visibility="collapsed")
    st.caption(f"Supported formats: {', '.join(t.upper() for t in SUPPORTED_TYPES)}  ·  "
               f"Max file size: {MAX_UPLOAD_MB}MB")

    with st.expander("Deal details (optional) — set client, region, deadline & reviewer", expanded=bool(up)):
        c1, c2 = st.columns(2)
        deal = c1.text_input("Deal / Project name", placeholder="e.g. Acme Cloud Migration RFP")
        client = c2.text_input("Client name", placeholder="e.g. Acme Corp")
        c3, c4, c5 = st.columns(3)
        region = c3.text_input("Region", placeholder="e.g. North America")
        
        deadline = c4.date_input(
            "Deadline",
            min_value=date.today()
        )
        role = c5.selectbox("Assign reviewer role", REVIEWER_ROLES)
        use_web = st.checkbox("Use live web search / pricing (Agent 2)", value=True)
    
    analyze = st.button(
        "⚡ Analyze & Generate Response",
        type="primary",
        use_container_width=True,
        disabled=up is None
    )

    if up and analyze:
        try:
            raw = extract_text(up.name, up.getvalue())
        except Exception as e:
            st.error(f"Could not read that file: {e}"); return
        if len(raw.strip()) < 30:
            st.error("That file has almost no readable text."); return
        if len(raw) < 100:
            st.error("The document contains very little readable text.")
            st.stop()

        # Optional: ensure enough words
        if len(raw.split()) < 20:
            st.error("The document does not contain enough content for analysis.")
            st.stop()

        RFP_KEYWORDS = [
            "proposal",
            "rfp",
            "requirements",
            "scope",
            "deliverables",
        ]

        text = raw.lower()

        matches = sum(keyword in text for keyword in RFP_KEYWORDS)

        if matches < 2:
            st.warning(
                "This document doesn't appear to be an RFP. "
                "Analysis may not produce the expected results."
            )
        rid = db.create_rfp(deal or up.name, client, region, deadline, "", "",
                            up.name, raw, role, "", use_web)
        print("=== Local DB Inserted ===")
        bar = st.progress(0.0, text="Starting…")
        try:
            url = os.getenv("BACKEND_URL") + "/health"

            print("Calling:", url)

            r = requests.get(url, timeout=10)

            print(r.status_code)
            print(r.text)
            print("=== Calling FastAPI ===")
            result = upload_rfp(
                uploaded_file=up,
                deal_name=deal,
                client_name=client,
                region=region,
                deadline=deadline,
                assigned_role=role,
                use_web_search=use_web,
            )
            bar.progress(1.0, text="Completed")
            rid = result["rfp_id"]
            print("=== FastAPI Returned ===")
        except Exception as e:
            st.error(str(e))
            print(str(e))
        finally:
            bar.empty()
        st.success("✅ Analysis complete. Opening Dashboard…")
        go("Dashboard", rid)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("<div class='card'><h3>📄 Upload Guidelines</h3>"
                    "<div class='muted' style='line-height:2'>"
                    "✅ Ensure the document is clear and readable<br>"
                    "✅ All pages should be included<br>"
                    f"✅ Supported formats: {', '.join(t.upper() for t in SUPPORTED_TYPES)}<br>"
                    f"✅ Maximum file size: {MAX_UPLOAD_MB}MB</div></div>", unsafe_allow_html=True)
    with g2:
        rows = ""
        for r in db.list_rfps()[:4]:
            rows += (f"<div class='feed'><div class='fi ic-red'>📕</div><div style='flex:1'>"
                     f"<div class='ft'>{r['file_name'] or r['deal_name']}</div>"
                     f"<div class='fd'>{(r.get('updated_at') or '')[:10]}</div></div></div>")
        st.markdown(f"<div class='card'><h3>🗂️ Recent Uploads</h3>{rows or '<div class=muted>No uploads yet.</div>'}</div>",
                    unsafe_allow_html=True)
