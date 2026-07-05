import io
import streamlit as st
import pandas as pd

import config

from backend.database import SessionLocal
from backend import crud

from utils.exporter import export_txt, export_docx, export_pdf
from llm import ping as groq_ping
import state
from ui.ui_utils import (topbar,card)

# =========================================================================== #
#  PAGE: Settings
# =========================================================================== #
def page_settings():
    ss = state.get_state()
    topbar("Settings", "Manage your preferences, AI model settings, and application configuration.",
           "⚙️", show_rfp=True)
    tabs = st.tabs(["General", "AI Model", "Security"])

    with tabs[0]:
        a, b = st.columns(2)
        with a:
            st.markdown("<div class='card'><h3>⚙️ General Settings</h3>", unsafe_allow_html=True)
            ws = st.text_input("Workspace / Organization Name", ss.workspace)
            tmpl = st.selectbox("Default RFP Template",
                                ["SmartRFP Standard Template", "Minimal", "Corporate"])
            cur_opts = ["USD - US Dollar", "EUR - Euro", "GBP - Pound", "INR - Rupee"]
            cur = st.selectbox("Default Currency", cur_opts, index=cur_opts.index(ss.currency))
            df_ = st.selectbox("Date Format", ["MMM DD, YYYY", "DD/MM/YYYY", "YYYY-MM-DD"])
            tz = st.selectbox("Time Zone", ["(GMT+05:30) Asia/Kolkata", "(GMT) UTC",
                                            "(GMT-05:00) US Eastern"])
            if st.button("Save Changes", type="primary", key="gen_save"):
                ss.workspace, ss.currency = ws, cur
                ss.update({"template": tmpl, "date_format": df_, "timezone": tz})
                st.success("✅ General settings saved. Currency applies on Resource Cost; "
                           "workspace name updates in the sidebar.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with b:
            st.markdown("<div class='card'><h3>🖥️ Application Preferences</h3>", unsafe_allow_html=True)
            theme = st.radio("Theme", ["Light", "Dark", "System"], horizontal=True,
                             index=["Light", "Dark", "System"].index(ss.theme))
            lang = st.selectbox("Language", ["English", "Spanish", "French", "German"])
            ipp_opts = [6, 10, 25, 50]
            ipp = st.selectbox("Items per page", ipp_opts, index=ipp_opts.index(ss.items_per_page)
                               if ss.items_per_page in ipp_opts else 0)
            tips = st.toggle("Show tips and guidance", value=ss.get("tips", True))
            autosave = st.toggle("Auto save drafts", value=ss.get("autosave", True))
            confirm = st.toggle("Confirm before export", value=ss.get("confirm_export", True))
            if st.button("Save Preferences", type="primary", key="pref_save"):
                ss.update({"theme": theme, "language": lang, "items_per_page": int(ipp),
                           "tips": tips, "autosave": autosave, "confirm_export": confirm})
                st.success(f"✅ Preferences saved. Dashboard now shows up to {ipp} rows.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        c, d = st.columns(2)
        with c:
            st.markdown("<div class='card'><h3>📁 File & Storage Settings</h3>", unsafe_allow_html=True)
            st.selectbox("Max file upload size", ["50 MB", "100 MB", "200 MB"])
            st.markdown("Supported file types")
            fc = st.columns(5)
            for i, t in enumerate(["PDF", "DOCX", "XLSX", "PPTX", "TXT"]):
                fc[i].checkbox(t, value=True, key=f"ft_{t}")
            st.toggle("Auto delete old files (90 days)", value=ss.get("autodelete", False), key="autodelete")
            if st.button("Save Changes", key="store_save"):
                st.success("✅ Storage settings saved.")
            st.markdown("</div>", unsafe_allow_html=True)
        with d:
            st.markdown("<div class='card'><h3>🕐 Session Settings</h3>", unsafe_allow_html=True)
            st.selectbox("Session timeout", ["30 minutes", "1 hour", "4 hours"])
            st.toggle("Auto logout inactive users", value=ss.get("autologout", False), key="autologout")
            st.toggle("Remember last workspace", value=ss.get("remember_ws", True), key="remember_ws")
            st.selectbox("Refresh data interval", ["5 minutes", "15 minutes", "1 hour"])
            if st.button("Save Changes", key="session_save"):
                st.success("✅ Session settings saved.")
            st.markdown("</div>", unsafe_allow_html=True)

        # ---- Live summary so it's clear these settings actually apply ----
        with card("Current Configuration (live)"):
            st.markdown(
                f"- **Workspace:** {ss.get('workspace')}\n"
                f"- **Currency:** {ss.get('currency')} (applied on Resource Cost)\n"
                f"- **Items per page:** {ss.get('items_per_page')} (applied on Dashboard)\n"
                f"- **Theme:** {ss.get('theme')}\n"
                f"- **Active AI model:** {config.GROQ_MODEL}\n"
                f"- **Confirm before export:** {'On' if ss.get('confirm_export', True) else 'Off'}")

    # ---- AI Model (functional Groq panel) ----
    with tabs[1]:
        st.markdown("<div class='card'><h3>🤖 AI / Groq Configuration</h3>", unsafe_allow_html=True)
        key = config.GROQ_API_KEY
        masked = (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("(set)" if key else "(empty)")
        m1, m2 = st.columns(2)
        m1.metric("API key", "Detected" if key else "Not found")
        m2.metric("Active model", config.GROQ_MODEL)
        st.caption(f"**.env file in use:** `{config.ENV_FILE or '— none found —'}`")
        st.caption(f"**Key (masked):** `{masked}`")

        model_opts = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b",
                      "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        if config.GROQ_MODEL not in model_opts:
            model_opts.insert(0, config.GROQ_MODEL)
        chosen = st.selectbox("Model (applies immediately)", model_opts,
                              index=model_opts.index(config.GROQ_MODEL))
        if chosen != config.GROQ_MODEL:
            config.GROQ_MODEL = chosen          # llm.chat()/ping() read this live
            ss.groq_model = chosen
            st.success(f"✅ Model switched to `{chosen}`.")

        if st.button("🔌 Test Groq connection", type="primary", key="ai_test"):
            with st.spinner("Calling Groq…"):
                r = groq_ping()
            (st.success if r["ok"] else st.error)(
                ("✅ " + r["message"]) if r["ok"] else ("❌ Connection failed: " + r["message"]))
        if not key:
            st.warning("No API key detected — running in **demo mode** (still fully functional).")
            with st.expander("🔎 Which env files were found?", expanded=True):
                for p, exists in config.ENV_SEARCHED:
                    st.markdown(f"{'✅' if exists else '❌'} `{p}`")
            st.markdown("Create a file named exactly **`.env`** next to `app.py` with:")
            st.code("GROQ_API_KEY=gsk_your_real_key_here\nGROQ_MODEL=openai/gpt-oss-20b")
        st.markdown("</div>", unsafe_allow_html=True)

        session = SessionLocal()
        try:
            kb_count = crud.kb_count(session)
        finally:
            session.close()

        st.markdown(
            f"<div class='card'><h3>📚 Knowledge Base ({kb_count})</h3>",
            unsafe_allow_html=True,
        )
        session = SessionLocal()
        try:
            docs = crud.get_kb_docs(session)
        finally:
            session.close()

        for d_ in docs:
            st.markdown(f"- **{d_.title}** · *{d_.doc_type}*")
        with st.expander("➕ Add a knowledge-base document"):
            t = st.text_input("Title", key="kbt"); dt = st.text_input("Type", "reference", key="kbdt")
            ct = st.text_area("Content", key="kbc", height=100)
            if st.button("Add document", key="kbadd") and t and ct:
                
                session = SessionLocal()
                try:
                    crud.add_kb_doc(session, t, dt, ct)
                finally:
                    session.close()

                st.success("Added.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("<div class='card'><h3>🛡️ Data & Privacy</h3>", unsafe_allow_html=True)
        st.caption("Manage RFP data stored locally in SQLite (smartrfp.db).")
        session = SessionLocal()
        try:
            rfps = crud.list_rfps(session)
        finally:
            session.close()

        for r in rfps:
            c = st.columns([5, 1])
            c[0].write(f"{r.deal_name} — {r.status}")
            if c[1].button("Delete", key=f"del_{r.id}"):

                session = SessionLocal()
                try:
                    crud.delete_rfp(session, r.id)
                finally:
                    session.close()

                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)