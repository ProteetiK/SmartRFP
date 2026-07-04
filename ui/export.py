import io
import streamlit as st
import pandas as pd

from ui import api

from ui.ui_utils import (topbar,current_rfp, go)

import state

# =========================================================================== #
#  PAGE: Export
# =========================================================================== #
def _html_export(rfp):
    secs = api.get_draft_sections(rfp["id"])
    body = "".join(f"<h2>{s['section_title']}</h2><p>{s['content']}</p>" for s in secs)
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>{rfp['deal_name']}</title>"
            f"<style>body{{font-family:Arial;max-width:800px;margin:40px auto;color:#0f172a}}"
            f"h1{{color:#2563eb}}h2{{margin-top:1.4em}}</style></head><body>"
            f"<h1>{rfp['deal_name']}</h1><p><b>Client:</b> {rfp.get('client_name') or '—'}</p>"
            f"{body}</body></html>")
    return html.encode("utf-8")


def _xlsx_export(rfp):
    pricing = api.get_pricing(rfp["id"])
    df = pd.DataFrame([{"Item": p["item"], "Qty": p["qty"], "Unit price": p["unit_price"],
                        "Total": p["total"], "Fetched": p["fetched_at"],
                        "Stale": "Yes" if p["stale"] else "No"} for p in pricing]) \
        if pricing else pd.DataFrame([{"Item": "(no pricing)"}])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name="Cost Estimate")
    return buf.getvalue()


FORMATS = [("PDF", "📕", "Best for sharing and printing"),
           ("Word (DOCX)", "📘", "Editable Word document"),
           ("Excel (XLSX)", "📗", "Cost & resource data only"),
           ("PowerPoint (PPTX)", "📙", "Executive summary presentation"),
           ("HTML", "🌐", "Web-friendly format"),
           ("Text (TXT)", "📄", "Plain text format")]

def page_export():
    ss = state.get_state()

    topbar("Export RFP Response", "Export your AI-generated RFP response in your preferred format.",
           "📤", show_rfp=True)
    if st.button(
        "💰 Go to Human Review",
        key="dashboard_human_review",
        type="primary",
        use_container_width=True,
        ):
        go("Human Review")
    rfp = current_rfp()
    if not rfp:
        st.info("No RFPs yet. Upload one to export."); return

    st.markdown("<div class='card'><h3>1. Select Export Format</h3>", unsafe_allow_html=True)
    fcols = st.columns(6)
    for i, (name, e, d) in enumerate(FORMATS):
        sel = ss.export_format == name
        fcols[i].markdown(f"<div class='fmtcard {'sel' if sel else ''}'><div class='e'>{e}</div>"
                          f"<div class='t'>{name}</div><div class='d'>{d}</div></div>", unsafe_allow_html=True)
        if fcols[i].button("Select", key=f"fmt_{name}", use_container_width=True):
            ss.export_format = name; st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)
    inc, opt = st.columns(2)
    with inc:
        st.markdown("**Include in Export**")
        for x in ["Cover Page & Executive Summary", "Requirements & Proposed Approach",
                  "Compliance & Security", "Resource Plan & Cost Estimate", "Appendices & References"]:
            st.checkbox(x, value=True, key=f"inc_{x}")
    with opt:
        st.markdown("**Export Options**")
        for x in ["Include Table of Contents", "Include Page Numbers", "Include Company Branding"]:
            st.checkbox(x, value=True, key=f"opt_{x}")
        st.selectbox("Branding", ["SmartRFP Default Template", "Minimal", "Corporate"])
    st.markdown("</div>", unsafe_allow_html=True)

    secs = api.get_draft_sections(rfp["id"])

    # summary + export
    s1, s2 = st.columns([1.2, 1])
    with s1:
        st.markdown(f"<div class='card'><h3>2. Export Summary</h3>"
                    f"<div class='muted' style='line-height:2'>"
                    f"📄 RFP Document — <span class='b'>{rfp['deal_name']}</span><br>"
                    f"📋 Total Sections — <span class='b'>{len(secs)}</span><br>"
                    f"📑 Estimated Pages — <span class='b'>24 – 30</span><br>"
                    f"💾 Format — <span class='b'>{ss.export_format}</span><br>"
                    f"🕐 Last Updated — <span class='b'>{(rfp.get('updated_at') or '')[:16]}</span>"
                    f"</div></div>", unsafe_allow_html=True)
    with s2:
        st.markdown("<div class='card'><h3>✅ Export Ready</h3>"
                    "<div class='muted'>Your RFP response is ready to be exported.</div><br>",
                    unsafe_allow_html=True)
        fmt = ss.export_format
        safe = "".join(ch if ch.isalnum() else "_" for ch in rfp["deal_name"])[:40] or "proposal"
        ok = True
        if ss.get("confirm_export", True):
            ok = st.checkbox("I confirm this proposal is ready to export", key="confirm_exp_chk")
        if not ok:
            st.caption("Tick the confirmation box to enable the download "
                       "(toggle off under Settings → Confirm before export).")
        try:
            if not ok:
                st.button("⬇️ Export Now", disabled=True, use_container_width=True)
            elif fmt == "PDF":
                st.download_button("⬇️ Export Now", api.export_bytes(rfp["id"], "pdf"), f"{safe}.pdf",
                                   "application/pdf", type="primary", use_container_width=True)
            elif fmt == "Word (DOCX)":
                st.download_button("⬇️ Export Now", api.export_bytes(rfp["id"], "docx"), f"{safe}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   type="primary", use_container_width=True)
            elif fmt == "Excel (XLSX)":
                st.download_button("⬇️ Export Now", _xlsx_export(rfp), f"{safe}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   type="primary", use_container_width=True)
            elif fmt == "HTML":
                st.download_button("⬇️ Export Now", _html_export(rfp), f"{safe}.html",
                                   "text/html", type="primary", use_container_width=True)
            elif fmt == "Text (TXT)":
                st.download_button("⬇️ Export Now", api.export_bytes(rfp["id"], "txt"), f"{safe}.txt",
                                   "text/plain", type="primary", use_container_width=True)
            else:  # PowerPoint placeholder -> export executive summary as TXT
                st.download_button("⬇️ Export Now (summary .txt)", api.export_bytes(rfp["id"], "txt"),
                                   f"{safe}.txt", "text/plain", type="primary", use_container_width=True)
                st.caption("PPTX generation isn't enabled in this build; exporting the summary as text.")
        except Exception as e:
            st.error(f"Export failed: {e}")
        if ok and rfp["status"] != "Rejected":
            api.log_action(rfp["id"], "Exported", rfp.get("assigned_role") or "Reviewer", fmt)
        st.markdown("</div>", unsafe_allow_html=True)

    st.info("🔒 Data Security: Exported files are generated on-demand and are not stored on our servers.")

    if st.button(
        "💰 Go to AI Evaluation",
        key="ai-eval",
        type="primary",
        use_container_width=True,
        ):
        go("AI Evaluation")