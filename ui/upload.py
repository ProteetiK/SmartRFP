import streamlit as st
from datetime import date

from backend.database import SessionLocal
from backend import crud

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
        rid = None  # ✅ ALWAYS initialize first

        try:
            raw = extract_text(up.name, up.getvalue())

            if len(raw.strip()) < 30:
                st.error("File too small")
                st.stop()

            if len(raw.split()) < 20:
                st.error("Not enough content")
                st.stop()

            RFP_KEYWORDS = ["proposal", "rfp", "requirements", "scope", "deliverables"]
            text = raw.lower()
            matches = sum(k in text for k in RFP_KEYWORDS)

            if matches < 2:
                st.warning("Not a valid RFP")

            bar = st.progress(0.0, text="Processing...")

            result = upload_rfp(
                uploaded_file=up,
                deal_name=deal,
                client_name=client,
                region=region,
                deadline=deadline,
                assigned_role=role,
                use_web_search=use_web,
            )

            rid = result.get("rfp_id")   # ✅ SAFE ACCESS

            bar.progress(1.0)
            st.success("Analysis complete")

        except Exception as e:
            st.error(f"Upload failed: {e}")

        finally:
            if "bar" in locals():
                bar.empty()

        # ✅ ONLY navigate if rid exists
        if rid is not None:
            go("Dashboard", rid)
        else:
            st.error("RFP ID not generated, cannot navigate")

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
        session = SessionLocal()

        try:
            rows_data = crud.list_rfps(session)
        finally:
            session.close()

        for r in rows_data[:4]:
           rows += (
                    f"<div class='feed'><div class='fi ic-red'>📕</div><div style='flex:1'>"
                    f"<div class='ft'>{r.file_name or r.deal_name}</div>"
                    f"<div class='fd'>{str(r.updated_at or '')[:10]}</div></div></div>"
                )
        st.markdown(f"<div class='card'><h3>🗂️ Recent Uploads</h3>{rows or '<div class=muted>No uploads yet.</div>'}</div>",
                    unsafe_allow_html=True)
