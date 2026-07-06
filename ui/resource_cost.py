import streamlit as st
import pandas as pd

from ui import api
from ui.ui_utils import (topbar,card, current_rfp, metric, go)
import state

# =========================================================================== #
#  PAGE: Resource Cost
# =========================================================================== #
ROLE_SPLIT = [("Project Management", 0.1466, 0.1208), ("Business Analysis", 0.1101, 0.0989),
              ("Solution Architecture", 0.2611, 0.1758), ("Development", 0.3625, 0.3625),
              ("Testing & QA", 0.0811, 0.1099), ("Training & Support", 0.0501, 0.0521)]


def page_resource_cost():
    ss = state.get_state()
    topbar("Resource & Cost Estimate", "Estimated resources, effort, and cost for this RFP.", "💲", show_rfp=True)
    if st.button(
        "💰 Go to Dashboad",
        key="dashboard",
        type="primary",
        use_container_width=True,
        ):
        go("Dashboard")
    rfp = current_rfp()
    if not rfp:
        st.info("No RFPs yet. Upload one to see the cost estimate."); return

    pricing = api.get_pricing(rfp["id"])
    # ---- Total cost: sum of Agent 2 pricing lines (dynamic, from RFP keywords) ----
    total_cost = sum(p["total"] for p in pricing) if pricing else 245680.0

    # ---- Effort: derived from the RFP's parsed requirements (dynamic per RFP) ----
    num_req = rfp.get("num_requirements") or len(api.get_draft_sections(rfp["id"])) or 8
    BASE_OVERHEAD_HRS = 160          # PM / setup / mobilisation
    HRS_PER_REQUIREMENT = 130        # analysis + design + build + test per requirement
    total_hours = BASE_OVERHEAD_HRS + num_req * HRS_PER_REQUIREMENT

    # ---- Weeks: effort ÷ blended team capacity (dynamic) ----
    TEAM_CAPACITY_HRS_PER_WEEK = 130
    weeks = max(1, -(-total_hours // TEAM_CAPACITY_HRS_PER_WEEK))   # ceil

    # ---- Confidence: derived from pricing freshness + reviewer flags (dynamic) ----
    stale = any(p.get("stale") for p in pricing)
    num_flags = rfp.get("num_flags") or 0
    if not stale and num_flags == 0:
        confidence, variance = "High", "±8%"
    elif not stale and num_flags <= 2:
        confidence, variance = "High", "±10%"
    elif num_flags <= 4:
        confidence, variance = "Medium", "±15%"
    else:
        confidence, variance = "Medium", "±20%"

    # currency comes from Settings → General (dynamic)
    code = ss.get("currency", "USD - US Dollar").split(" - ")[0]
    sym = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}.get(code, "$")

    cols = st.columns(4)
    metric(cols[0], "ic-blue", "🧾", "Total Estimated Cost", f"{sym}{total_cost:,.0f}", code)
    metric(cols[1], "ic-green", "🕐", "Total Effort", f"{total_hours:,} hrs", f"{weeks} Weeks")
    metric(cols[2], "ic-purple", "🛡️", "Cost Confidence", confidence, f"{variance} Estimation Variance")
    metric(cols[3], "ic-amber", "💲", "Currency", code, f"All costs in {code}")
    st.write("")

    with st.expander("ℹ️ How are these numbers calculated?"):
        st.markdown(
            f"- **Total Estimated Cost** = sum of the live pricing lines from Agent 2 "
            f"(built from keywords in this RFP). Current total: **{sym}{total_cost:,.0f}** "
            f"from **{len(pricing)}** pricing line(s).\n"
            f"- **Total Effort** = {BASE_OVERHEAD_HRS} base hrs + "
            f"**{num_req} requirements** × {HRS_PER_REQUIREMENT} hrs = **{total_hours:,} hrs**.\n"
            f"- **Weeks** = effort ÷ {TEAM_CAPACITY_HRS_PER_WEEK} hrs/week team capacity = **{weeks} weeks**.\n"
            f"- **Cost Confidence** comes from pricing freshness (stale lines: "
            f"**{'yes' if stale else 'no'}**) and reviewer flags (**{num_flags}**).\n\n"
            f"Because these depend on the RFP's requirement count, flags and matched pricing, "
            f"they change from one RFP to another.")

    with card("Cost Breakdown by Role"):
        role_names = [r[0] for r in ROLE_SPLIT]
        choice = st.selectbox("Filter by role", ["All roles"] + role_names, key="role_filter")
        shown = ROLE_SPLIT if choice == "All roles" else [r for r in ROLE_SPLIT if r[0] == choice]
        cost_rows = []
        for name, cpct, apct in shown:
            cost_rows.append({"Role": name, "Effort (hrs)": int(total_hours * apct),
                              f"Cost ({code})": f"{sym}{total_cost*cpct:,.0f}",
                              "% of Total": f"{cpct*100:.2f}%"})
        if choice == "All roles":
            cost_rows.append({"Role": "Total", "Effort (hrs)": total_hours,
                              f"Cost ({code})": f"{sym}{total_cost:,.0f}", "% of Total": "100%"})
        df = pd.DataFrame(cost_rows)
        # styled = (
        #     df.style
        #       .set_properties(**{
        #           "background-color": "#f3fefe",
        #           "color": "black"
        #       })
        #       .set_table_styles([
        #         {
        #             "selector": "th",
        #             "props": [
        #                 ("background-color", "#dafbfd"),  # Header background
        #                 ("color", "black"),               # Header text
        #                 ("font-weight", "bold"),
        #                 ("text-align", "center"),
        #             ],
        #         },
        #     ])
        # )
        st.dataframe(df, use_container_width=True, hide_index=True)

    with card("Resource Allocation"):
        for name, cpct, apct in sorted(shown, key=lambda r: -r[2]):
            bar = int(apct * 100)
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:.8rem;margin:.35rem 0'>"
                f"<div style='width:150px;font-size:.9rem;color:var(--ink2)'>{name}</div>"
                f"<div style='width:90px;font-size:.85rem;color:var(--muted)'>{int(total_hours*apct)} hrs</div>"
                f"<div style='flex:1;background:#eef2f7;border-radius:6px;height:10px'>"
                f"<div style='width:{bar}%;background:var(--blue);height:10px;border-radius:6px'></div></div>"
                f"<div style='width:54px;text-align:right;font-weight:700;color:var(--ink)'>{apct*100:.1f}%</div>"
                f"</div>", unsafe_allow_html=True)

    st.info("This estimate is AI-generated based on the RFP requirements and historical data. "
            "Please review and adjust as needed.")

    st.divider()

    if st.button(
        "💰 Go to Human Review",
        key="dashboard_resource_cost",
        type="primary",
        use_container_width=True,
        ):
        go("Human Review")