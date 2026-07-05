import streamlit as st
import pandas as pd
from backend.database import SessionLocal
from backend import crud

from ui.ui_utils import (topbar,card,current_rfp, pill, go)
from .api import (regenerate)

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
    session = SessionLocal()

    try:
        sections = crud.get_draft_sections(session, rfp.id)
    finally:
        session.close()

    st.write("Current RFP ID:", rfp.id)
    st.write("Current Deal:", rfp.deal_name)
    st.write("Sections Found:", len(sections))
    if not rfp:
        st.info("No RFPs yet. Upload one to review."); return

    session = SessionLocal()
    try:
        sections = crud.get_draft_sections(session, rfp.id)
    finally:
        session.close()

    if not sections:
        st.info("This RFP has no draft yet."); return

    reviewer = rfp.assigned_to or rfp.assigned_role or "Reviewer"
    main, rightc = st.columns([2.7, 1.1])

    # --- Full proposal (all sections in one view, no per-section approval) ---
    with main:
        with card():
            st.markdown(f"<div class='cardtitle' style='display:flex;justify-content:space-between'>"
                        f"<span>{rfp.deal_name}</span>{pill(rfp.status)}</div>",
                        unsafe_allow_html=True)
            for s in sections:
                st.markdown(f"#### {s.section_title}")
                st.markdown(s.content)
                if s.source:
                    refs = "".join(
                        f"<span class='refpill'>{x.strip()}</span>"
                        for x in s.source.split(",")
                    )
                    st.markdown(f"<div class='muted' style='margin-top:.2rem'>Source: </div>{refs}",
                                unsafe_allow_html=True)
                with st.expander("✏️ Edit this section"):
                    new = st.text_area("content", value=s.content, height=200,
                                       label_visibility="collapsed", key=f"edit_{s.id}")
                    if st.button("💾 Save", key=f"save_{s.id}"):
                        session = SessionLocal()

                        try:
                           crud.update_draft_section(session, s.id, new)
                        finally:
                            session.close()


                        session = SessionLocal()

                        try:
                            crud.log_action(
                                session,
                                rfp.id,
                                "Edited section",
                                reviewer,
                                s.section_title,
                            )
                        finally:
                            session.close()
                        st.toast("Saved."); st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)

    # --- Whole-proposal actions ---
    with rightc:
        with card("Review Actions"):
            comment = st.text_area("Reviewer comments", placeholder="Add a comment…",
                                   key="review_comment", height=90)
            if st.button("✅ Approve Proposal", use_container_width=True, key="approve_all"):
                session = SessionLocal()

                try:
                    crud.update_rfp_status(session, rfp.id, "Approved")
                finally:
                    session.close()

                

                session = SessionLocal()

                try:
                    crud.log_action(
                        session,
                        rfp.id,
                        "Approved",
                        reviewer,
                        comment.strip()[:80] or "Proposal approved",
                    )
                finally:
                    session.close()
                st.toast("Proposal approved.")
                st.rerun()
            if st.button("✏️ Request Changes", use_container_width=True, key="req_changes"):
                session = SessionLocal()

                try:
                    crud.update_rfp_status(session, rfp.id, "In Review")
                finally:
                    session.close()
                    
     

                session = SessionLocal()

                try:
                    crud.log_action(
                        session,
                        rfp.id,
                        "Changes requested",
                        reviewer,
                        comment.strip()[:80] or "Changes requested",
                    )
                finally:
                    session.close()
                st.toast("Changes requested."); st.rerun()
            if st.button("💬 Add Comment", use_container_width=True, key="add_cmt"):
                if comment.strip():
                    
                    session = SessionLocal()

                    try:
                        crud.log_action(
                            session,
                            rfp.id,
                            "Comment added",
                            reviewer,
                            comment.strip()[:80],
                        )
                    finally:
                        session.close()
                    st.toast("Comment added.")
                else:
                    st.toast("Type a comment first.")
                st.rerun()
            if st.button("🔄 Regenerate Draft", use_container_width=True, key="regen_all"):
                with st.spinner("Regenerating draft..."):
                    result = regenerate(rfp.id)
                if result["success"]:
                    st.toast("Draft regenerated.")
                    st.rerun()
                else:
                    st.error(result["message"])
        with card("Review Information"):
            st.markdown(f"<div class='muted'>Reviewer</div><div class='b'>{reviewer}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Status</div><div>{pill(rfp.status)}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Sections</div>"
                        f"<div class='b'>{len(sections)}</div>"
                        f"<div class='muted' style='margin-top:.5rem'>Last Updated</div>"
                        f"<div class='b'>{str(rfp.updated_at or '')[:16]}</div>", unsafe_allow_html=True)
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
        session = SessionLocal()

        try:
            log = crud.get_audit_log(session, rfp.id)
        finally:
            session.close()
        if log:
            st.dataframe(pd.DataFrame([{
                                    "Reviewer": a.actor,
                                    "Action": a.action,
                                    "Detail": a.detail or "",
                                    "Time": a.timestamp,
                                }
                                for a in log][::-1]), use_container_width=True, hide_index=True)
        else:
            st.caption("No history yet.")