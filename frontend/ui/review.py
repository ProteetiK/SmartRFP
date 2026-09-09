import streamlit as st
import pandas as pd
from ui import api

from ui.ui_utils import (topbar,card,current_rfp, pill, go)

# =========================================================================== #
#  PAGE: Human Review
# =========================================================================== #

def page_review():
    topbar("Human Review & Approval", "Review the AI-generated proposal and provide feedback.",
           "🗂️", show_rfp=True)
    if st.button(
        "💰 Go to Resource Cost",
        key="resource_cost",
        type="primary",
        use_container_width=True,
        ):
        go("Resource Cost")
    rfp = current_rfp()
    if not rfp:
        st.info("No RFPs yet. Upload one to review."); return
    sections = api.get_draft_sections(rfp["id"])
    if not sections:
        st.info("This RFP has no draft yet."); return

    reviewer = rfp.get("assigned_to") or rfp.get("assigned_role") or "Reviewer"
    main, rightc = st.columns([2.7, 1.1])

    # --- Full proposal (all sections in one view, no per-section approval) ---
    with main:
        with card():
            st.markdown(f"<div class='cardtitle' style='display:flex;justify-content:space-between'>"
                        f"<span>{rfp['deal_name']}</span>{pill(rfp['status'])}</div>",
                        unsafe_allow_html=True)
            for s in sections:
                st.markdown(f"#### {s['section_title']}")
                st.markdown(s["content"])
                if s.get("source"):
                    refs = "".join(f"<span class='refpill'>{x.strip()}</span>"
                                   for x in (s["source"] or "").split(",") if x.strip())
                    st.markdown(f"<div class='muted' style='margin-top:.2rem'>Source: </div>{refs}",
                                unsafe_allow_html=True)
                with st.expander("✏️ Edit this section"):
                    new = st.text_area("content", value=s["content"], height=200,
                                       label_visibility="collapsed", key=f"edit_{s['id']}")
                    if st.button("💾 Save", key=f"save_{s['id']}"):
                        api.update_draft_section(s["id"], new)
                        api.log_action(rfp["id"], "Edited section", reviewer, s["section_title"])
                        st.toast("Saved."); st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)

        with card("Pricing Review"):
            pricing = api.get_pricing(rfp["id"])
            df = pd.DataFrame(pricing)
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                disabled=["source"],
            )

            # Convert editable columns to numbers
            edited["qty"] = (
                pd.to_numeric(edited["qty"], errors="coerce")
                .fillna(1)
            )

            edited["unit_price"] = (
                pd.to_numeric(edited["unit_price"], errors="coerce")
                .fillna(0)
            )

            edited["total"] = (
                edited["qty"] * edited["unit_price"]
            ).round(2)

            # Recalculate totals
            edited["total"] = (
                edited["qty"].fillna(1) *
                edited["unit_price"].fillna(0)
            ).round(2)

            # Keep margin row unchanged
            mask = edited["item"].str.contains("Margin", case=False, na=False)
            edited.loc[mask, "total"] = df.loc[mask, "total"]
            if st.button("💾 Save Pricing"):
                api.update_pricing(
                    rfp["id"],
                    edited.to_dict("records")
                )
                st.toast("Pricing updated")
                st.rerun()

    # --- Whole-proposal actions ---
    with rightc:
        with card("Review Actions"):
            comment = st.text_area("Reviewer comments", placeholder="Add a comment…",
                                   key="review_comment", height=90)
            if st.button("✅ Approve Proposal", use_container_width=True, key="approve_all"):
                api.set_status(rfp["id"], "Approved", comment.strip()[:80] or "Proposal approved")
                api.log_action(rfp["id"], "Approved", reviewer,
                              comment.strip()[:80] or "Proposal approved")
                st.toast("Proposal approved.")
                st.rerun()
            if st.button("✏️ Request Changes", use_container_width=True, key="req_changes"):
                api.set_status(rfp["id"], "In Review", comment.strip()[:80] or "Changes requested")
                api.log_action(rfp["id"], "Changes requested", reviewer,
                              comment.strip()[:80] or "Changes requested")
                st.toast("Changes requested."); st.rerun()
            if st.button("💬 Add Comment", use_container_width=True, key="add_cmt"):
                if comment.strip():
                    api.log_action(rfp["id"], "Comment added", reviewer, comment.strip()[:80])
                    st.toast("Comment added.")
                else:
                    st.toast("Type a comment first.")
                st.rerun()
            if st.button("🔄 Regenerate Draft", use_container_width=True, key="regen_all"):
                with st.spinner("Regenerating draft..."):
                    try:
                        result = api.regenerate(rfp["id"])
                    except api.APIError as e:
                        result = {"success": False, "message": str(e)}
                if result["success"]:
                    st.toast("Draft regenerated.")
                    st.rerun()
                else:
                    st.error(result["message"])
        with card("Review Information"):
            st.markdown(f"<div class='muted'>Reviewer</div><div class='b'>{reviewer}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Status</div><div>{pill(rfp['status'])}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Sections</div>"
                        f"<div class='b'>{len(sections)}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Last Updated</div>"
                        f"<div class='b'>{(rfp.get('updated_at') or '')[:16]}</div>", unsafe_allow_html=True)
            st.divider()
        if st.button(
            "💰 Go to Export",
            key="export",
            type="primary",
            use_container_width=True,
            ):
            go("Export")

    # --- History ---
    with card("Review History"):
        log = api.get_audit_log(rfp["id"])
        if log:
            st.dataframe(pd.DataFrame([{"Reviewer": a["actor"], "Action": a["action"],
                                        "Detail": a.get("detail") or "", "Time": a["timestamp"]}
                                       for a in log][::-1]), use_container_width=True, hide_index=True)
        else:
            st.caption("No history yet.")