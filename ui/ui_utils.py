from contextlib import contextmanager
import streamlit as st
from backend.database import SessionLocal
from backend import crud

import state

def go(page, rfp_id=None):
    ss = state.get_state()
    ss.page = page
    if rfp_id is not None:
        ss.current_rfp = rfp_id
    st.rerun()

PILL = {"In Review": "p-rev", "Drafting": "p-ana", "Analyzed": "p-ana", "Approved": "p-app",
        "Exported": "p-exp", "Uploaded": "p-pend", "Pending": "p-pend", "Rejected": "p-rej"}

def pill(text, cls=None):
    return f"<span class='pill {cls or PILL.get(text,'p-pend')}'>{text}</span>"

# =========================================================================== #
#  SHARED helpers
# =========================================================================== #
def topbar(title, subtitle, icon="", show_rfp=False):
    ss = state.get_state()

    left, right = st.columns([3, 1.5])
    with left:
        st.markdown(f"<div class='tb'><div><h1>{icon} {title}</h1>"
                    f"<div class='sub'>{subtitle}</div></div></div>", unsafe_allow_html=True)
    with right:
        if show_rfp:
            cols = st.columns([2.9, 0.75, 0.75, 0.75])
        else:
            cols = st.columns([2.9, 0.75, 0.75, 0.75])

        if show_rfp:
            session = SessionLocal()

            try:
                rfps = crud.list_rfps(session)
            finally:
                session.close()

            if rfps:
                ids = [r.id for r in rfps]
                lbl = {r.id: r.deal_name for r in rfps}
                cur = ss.current_rfp if ss.current_rfp in ids else ids[0]

                sel = cols[0].selectbox(
                    "RFP",
                    ids,
                    index=ids.index(cur),
                    format_func=lambda i: lbl[i],
                    label_visibility="collapsed",
                    key=f"rfpsel_{title}",
                )
                ss.current_rfp = sel

        with cols[1]:
            st.markdown("<div class='avatar'>👤</div>", unsafe_allow_html=True)

        with cols[2]:
            if st.button("⚙", key=f"settings_{title}_1", help="Settings"):
                go("Settings")
        
        with cols[3]:
            if st.button("❓", key=f"help_{title}_1", help="Help"):
                go("Help & Docs")

def metric(col, ic, icon, label, value, sub):
    col.markdown(f"<div class='metric'><div class='top'><div class='lab'>{label}</div>"
                 f"<div class='ic {ic}'>{icon}</div></div><div class='val'>{value}</div>"
                 f"<div class='sub'>{sub}</div></div>", unsafe_allow_html=True)

@contextmanager
def card(title=None):
    """A real bordered container so Streamlit widgets sit INSIDE the box."""
    box = st.container(border=True)
    with box:
        if title:
            st.markdown(f"<div class='cardtitle'>{title}</div>", unsafe_allow_html=True)
        yield box


def current_rfp():
    ss = state.get_state()

    session = SessionLocal()

    try:
        rfps = crud.list_rfps(session)

        if not rfps:
            return None

        ids = [r.id for r in rfps]

        rid = ss.current_rfp if ss.current_rfp in ids else ids[0]

        ss.current_rfp = rid

        return crud.get_rfp(session, rid)

    finally:
        session.close()


def exported_ids():
    session = SessionLocal()

    try:
        out = set()

        rfps = crud.list_rfps(session)

        for r in rfps:
            logs = crud.get_audit_log(session, r.id)

            for a in logs:
                if "export" in (a.action or "").lower():
                    out.add(r.id)
                    break

        return out

    finally:
        session.close()
def _rev_key(rid, sid): return f"{rid}:{sid}"
