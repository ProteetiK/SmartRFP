import streamlit as st
import pandas as pd
import altair as alt

from ui import api

from ui.ui_utils import (topbar,exported_ids,metric, card, pill, go)

import state

# =========================================================================== #
#  PAGE: Dashboard
# =========================================================================== #
def page_dashboard():
    ss = state.get_state()
    topbar("Dashboard", "Overview of your RFP analysis and proposal generation pipeline.", "📊")

    rfps = api.list_rfps()
    exp = exported_ids()
    total = len(rfps)
    analyzed = sum(1 for r in rfps if r["status"] != "Uploaded")
    in_review = sum(1 for r in rfps if r["status"] == "In Review")
    approved = sum(1 for r in rfps if r["status"] == "Approved")
    exported = len(exp)

    cols = st.columns(5)
    metric(cols[0], "ic-purple", "📄", "Total RFPs", total, "All time")
    metric(cols[1], "ic-blue", "📊", "Analyzed", analyzed, "This month")
    metric(cols[2], "ic-amber", "🕐", "In Review", in_review, "Pending review")
    metric(cols[3], "ic-green", "✅", "Approved", approved, "This month")
    metric(cols[4], "ic-teal", "📤", "Exported", exported, "This month")
    st.write("")

    # ---- Donut ----
    if 1:
        with card("RFP Status Overview"):
            drafting = sum(1 for r in rfps if r["status"] == "Drafting")
            others = sum(1 for r in rfps if r["status"] in ("Uploaded", "Rejected"))
            data = pd.DataFrame({
                "Status": ["Analyzed", "In Review", "Approved", "Exported", "Others"],
                "Count": [max(analyzed - in_review - approved, drafting),
                          in_review, approved, exported, others],
            })
            tot = int(data["Count"].sum())
            if tot == 0:
                st.info("No RFPs yet — upload one to see the breakdown.")
            else:
                data["pct"] = (data["Count"] / tot * 100).round(0).astype(int)

                data["label"] = data.apply(
                    lambda r: f'{int(r["Count"])} ({r["pct"]}%)'
                    if r["Count"] > 0 else "",
                    axis=1,
                )

                # EY Dark Theme Palette
                rng = [
                    "#FFE600",  # EY Yellow
                    "#8C8C8C",  # Medium Gray
                    "#00A3A1",  # EY Teal
                    "#6D6E71",  # Dark Gray
                    "#FFFFFF",  # White
                ]

                base = (
                    alt.Chart(data)
                    .encode(
                        theta=alt.Theta("Count:Q", stack=True),
                        color=alt.Color(
                            "Status:N",
                            scale=alt.Scale(
                                domain=list(data["Status"]),
                                range=rng,
                            ),
                            legend=alt.Legend(
                                title=None,
                                orient="right",
                                labelColor="white",
                                symbolStrokeColor="white",
                            ),
                        ),
                        tooltip=["Status", "Count", "pct"],
                    )
                )

                arc = base.mark_arc(
                    innerRadius=62,
                    outerRadius=104,
                )

                txt = base.mark_text(
                    radius=125,
                    fontSize=11,
                    fontWeight="bold",
                    color="white",
                ).encode(
                    text="label:N",
                )

                chart = (
                    arc + txt
                ).properties(
                    height=300,
                    background="#000",
                ).configure_view(
                    strokeWidth=0,
                ).configure_legend(
                    labelColor="white",
                ).configure_axis(
                    labelColor="white",
                    titleColor="white",
                )

                st.altair_chart(chart, use_container_width=True)

    if 1:
        with card("Recent RFPs"):
            if rfps:
                n = int(ss.get("items_per_page", 6))
                hc = st.columns([2.3, 1.6, 1.3, 1.4, 0.6])
                for c, t in zip(hc, ["RFP Name", "Client", "Status", "Last Updated", ""]):
                    c.markdown(f"<span class='muted' style='font-weight:700;font-size:.8rem'>{t}</span>",
                               unsafe_allow_html=True)
                for r in rfps[:n]:
                    c = st.columns([2.3, 1.6, 1.3, 1.4, 0.6])
                    c[0].write(r["deal_name"])
                    c[1].write(r.get("client_name") or "—")
                    c[2].markdown(pill(r["status"]), unsafe_allow_html=True)
                    c[3].write((r.get("updated_at") or "")[:10])
                    if c[4].button("🗑️", key=f"dashdel_{r['id']}", help="Delete this RFP",
                                   use_container_width=True):
                        api.delete_rfp(r["id"]); st.toast("RFP deleted."); st.rerun()
            else:
                st.info("No RFPs yet.")
            if st.button("View all →", key="dash_viewall"):
                go("Human Review")

    # ---- Pipeline + AI insights ----
    pcol, icol = st.columns([1.4, 1])
    with pcol:
        with card("Pipeline Progress"):
            steps = [("☁️", "Upload", "done"), ("📄", "Analyze", "done"),
                     ("⚙️", "Costing", "prog"), ("🧑‍⚖️", "Review", "pend"), ("📤", "Export", "pend")]
            sc = st.columns([2, 1, 2, 1, 2, 1, 2, 1, 2])
            order = [0, None, 1, None, 2, None, 3, None, 4]
            statelab = {"done": "Completed", "prog": "In Progress", "pend": "Pending"}
            statecol = {"done": "var(--green)", "prog": "var(--blue)", "pend": "var(--muted)"}
            for i, slot in enumerate(order):
                if slot is None:
                    sc[i].markdown("<div class='arrow'>→</div>", unsafe_allow_html=True)
                else:
                    e, n, s = steps[slot]
                    sc[i].markdown(f"<div class='step'><div class='c {s}'>{e}</div><div class='n'>{n}</div>"
                                   f"<div class='s' style='color:{statecol[s]}'>{statelab[s]}</div></div>",
                                   unsafe_allow_html=True)
    with icol:
        with card("AI Insights"):
            st.markdown("<div class='muted'>Most common requirement category</div>"
                        "<div style='margin:.3rem 0 .8rem'><span class='refpill'>Security &amp; Compliance</span></div>"
                        "<div class='muted'>Average proposal length</div>"
                        "<div style='margin-top:.3rem'><span class='refpill'>24 pages</span></div>",
                        unsafe_allow_html=True)

    st.divider()

    if st.button(
        "💰 Go to Resource Cost",
        key="dashboard_resource_cost",
        type="primary",
        use_container_width=True,
        ):
        go("Resource Cost")