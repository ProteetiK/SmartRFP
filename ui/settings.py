import io
import streamlit as st
import pandas as pd

import config
from ui import api
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
                f"- **Confirm before export:** {'On' if ss.get('confirm_export', True) else 'Off'}")

    # ---- AI Model (backend-driven Groq status panel) ----
    # Fix note: this used to read config.GROQ_API_KEY / config.GROQ_MODEL and
    # call llm.ping() directly from inside the Streamlit process -- meaning
    # the frontend needed its own copy of GROQ_API_KEY and called Groq
    # itself, bypassing the backend entirely. It now asks the backend's
    # /health/llm endpoint, which is the only place that should hold that
    # key. The frontend no longer needs (or reads) any LLM credentials.
    with tabs[1]:
        st.markdown("<div class='card'><h3>🤖 AI Model Status</h3>", unsafe_allow_html=True)
        status = api.llm_status()
        m1, m2 = st.columns(2)
        m1.metric("Backend LLM", "Connected" if status.get("ok") else "Unavailable")
        m2.metric("Active model", status.get("model", "?"))
        if status.get("failover_configured"):
            st.caption("OpenAI failover is configured on the backend.")
        st.caption(
            "The model is configured server-side via `GROQ_MODEL` in the backend's "
            "`.env` -- change it there and restart the backend to switch models."
        )

        if st.button("🔌 Test backend LLM connection", type="primary", key="ai_test"):
            with st.spinner("Asking the backend to call Groq…"):
                status = api.llm_status()
            (st.success if status.get("ok") else st.error)(
                ("✅ " + status.get("message", "")) if status.get("ok")
                else ("❌ Connection failed: " + status.get("message", "")))
        if not status.get("ok"):
            st.warning(
                "The backend could not reach Groq. Check `GROQ_API_KEY` / `GROQ_MODEL` "
                "in the backend's `.env` and that the backend process was restarted "
                "after any change."
            )
        st.markdown("</div>", unsafe_allow_html=True)

        kb = api.get_kb_docs()
        st.markdown("<div class='card'><h3>📚 Knowledge Base ({}) </h3>".format(api.kb_count()),
                    unsafe_allow_html=True)
        for d_ in kb:
            indexed = " ✅ indexed in Pinecone" if d_.get("pinecone_indexed") else " ⏳ not yet searchable"
            st.markdown(f"- **{d_['title']}** · *{d_['doc_type']}*{indexed}")
        with st.expander("➕ Add a knowledge-base document"):
            t = st.text_input("Title", key="kbt"); dt = st.text_input("Type", "reference", key="kbdt")
            ct = st.text_area("Content", key="kbc", height=100)
            if st.button("Add document", key="kbadd") and t and ct:
                api.add_kb_doc(t, dt, ct); st.success("Added — indexing into Pinecone now."); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("<div class='card'><h3>🛡️ Data & Privacy</h3>", unsafe_allow_html=True)
        st.caption("Manage RFP data stored in PostgreSQL. Uploaded document content "
                   "is also embedded into Pinecone under a per-RFP namespace.")
        for r in api.list_rfps():
            c = st.columns([5, 1])
            c[0].write(f"{r['deal_name']} — {r['status']}")
            if c[1].button("Delete", key=f"del_{r['id']}"):
                api.delete_rfp(r["id"]); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)