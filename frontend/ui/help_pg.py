import streamlit as st
import state
from ui.ui_utils import (topbar,card)


# =========================================================================== #
#  PAGE: Help & Docs
# =========================================================================== #
def page_help():
    ss = state.get_state()
    topbar("Help & Documentation", "Find answers, learn how to use SmartRFP, and get the support you need.",
           "❓", show_rfp=True)
    q = st.text_input("Search", placeholder="Search for help articles, guides, and more…",
                      label_visibility="collapsed").strip().lower()

    GUIDES = {
        "Getting Started": ("☁️", "ic-blue",
            "Learn the basics and set up your first RFP analysis.",
            "1. Open **Upload** and drop a PDF, DOCX or TXT RFP (max 50 MB).\n"
            "2. Optionally set the deal name, client, region, deadline and reviewer role.\n"
            "3. Click **Analyze & Generate Response** — the pipeline parses requirements, runs "
            "RAG retrieval and pricing in parallel, then writes a draft.\n"
            "4. You land on the **Dashboard**; open the RFP in **Human Review** to approve it, "
            "then **Export**."),
        "Dashboard Guide": ("📊", "ic-green",
            "Understand dashboard insights and key metrics.",
            "The five cards show Total RFPs, Analyzed, In Review, Approved and Exported. The donut "
            "breaks RFPs down by status. **Recent RFPs** lists the latest deals, **Pipeline Progress** "
            "shows the current stage, and the **Activity Feed** is built from the audit log."),
        "Resource & Cost": ("💲", "ic-purple",
            "Learn how resource estimation and cost calculation works.",
            "The total cost is summed from the pricing lines produced by Agent 2. Effort is split "
            "across roles (PM, BA, Solution Architecture, Development, QA, Training) using standard "
            "rate-card percentages, shown in the **Cost Breakdown by Role** table and the "
            "**Resource Allocation** bars. Treat figures as estimates and adjust before quoting."),
        "Human Review": ("🗂️", "ic-amber",
            "Review AI-generated content and provide feedback.",
            "Pick a section on the left, edit it in the editor, and use **Approve Section**, "
            "**Request Changes**, **Add Comment** or **Regenerate Section**. Each section shows its "
            "source references and an AI confidence score. When all sections are approved the RFP "
            "status becomes Approved. Everything is recorded in **Review History**."),
        "Export & Reports": ("📤", "ic-red",
            "Export RFP responses in multiple formats and options.",
            "Choose a format (PDF, Word, Excel, PowerPoint or HTML), tick the include options, then "
            "click **Export Now** to download. PDF/DOCX/HTML contain the full proposal; XLSX contains "
            "the cost data. Files are generated on demand and not stored on a server."),
        "Settings": ("⚙️", "ic-teal",
            "Configure application preferences and the Groq model.",
            "**General** holds workspace, currency, date and storage preferences. **AI Model** is where "
            "you confirm the Groq key is detected and run **Test Groq connection**. **Security** lets you "
            "delete RFP data stored locally in SQLite."),
    }

    ss.setdefault("help_topic", None)
    st.markdown("### How can we help you?")
    names = list(GUIDES.keys())
    for row in range(0, len(names), 3):
        cols = st.columns(3)
        for j, name in enumerate(names[row:row + 3]):
            e, ic, desc, _ = GUIDES[name]
            with cols[j]:
                st.markdown(f"<div class='helpcard'><div class='ic {ic}'>{e}</div>"
                            f"<div class='t'>{name}</div><div class='d'>{desc}</div></div>",
                            unsafe_allow_html=True)
                if st.button("View Guide →", key=f"guide_{name}", use_container_width=True):
                    ss.help_topic = None if ss.help_topic == name else name
                    st.rerun()

    if ss.help_topic:
        e, ic, desc, body = GUIDES[ss.help_topic]
        st.markdown(f"<div class='card'><h3>{e} {ss.help_topic}</h3>", unsafe_allow_html=True)
        st.markdown(body)
        if st.button("✕ Close guide", key="close_guide"):
            ss.help_topic = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    kb, faq = st.columns(2)
    with kb:
        st.markdown("<div class='card'><h3>Knowledge Base</h3>", unsafe_allow_html=True)
        ARTICLES = {
            "How to upload and analyze an RFP":
                ("Getting Started", "Go to Upload → drop your file → (optionally) fill deal details → "
                 "click Analyze & Generate Response. The pipeline extracts requirements, retrieves "
                 "internal context and pricing, then drafts the proposal."),
            "Understanding the Dashboard":
                ("Dashboard", "Metric cards summarise pipeline volume; the donut shows status mix; the "
                 "activity feed reflects real audit-log events."),
            "Resource Estimation Explained":
                ("Resource & Cost", "Total cost comes from the pricing lines; effort is allocated across "
                 "roles by rate-card percentages and shown as a table plus allocation bars."),
            "Review and Approve AI Content":
                ("Human Review", "Approve, request changes, comment or regenerate each section. Source "
                 "references and a confidence score help you verify before approving."),
            "Export RFP Responses":
                ("Export", "Select a format and click Export Now. PDF/DOCX/HTML carry the full proposal; "
                 "XLSX carries the cost table."),
            "Application Settings Overview":
                ("Settings", "Set preferences under General, verify the Groq key under AI Model, and "
                 "manage local data under Security."),
        }
        for title, (tag, body) in ARTICLES.items():
            if q and q not in title.lower() and q not in body.lower():
                continue
            with st.expander(f"📄 {title}"):
                st.markdown(f"<span class='refpill'>{tag}</span>", unsafe_allow_html=True)
                st.write(body)
        st.markdown("</div>", unsafe_allow_html=True)
    with faq:
        st.markdown("<div class='card'><h3>Frequently Asked Questions</h3>", unsafe_allow_html=True)
        faqs = {
            "How does SmartRFP analyze my documents?":
                "It extracts requirements, runs a RAG search over your knowledge base plus a "
                "pricing agent, then synthesizes a draft proposal with risk flags.",
            "Is my data secure?":
                "Data is stored locally in SQLite and exports are generated on-demand.",
            "Can I collaborate with my team?":
                "Assign reviewer roles (Junior/Senior/Supervisor/SME) and filter the dashboard by role.",
            "What export formats are supported?":
                "PDF, Word (DOCX), Excel (XLSX) and HTML are generated directly.",
            "How accurate are the cost estimates?":
                "Estimates are AI/heuristic-generated from requirements and a rate card; review before quoting.",
        }
        for qn, a in faqs.items():
            if q and q not in qn.lower() and q not in a.lower():
                continue
            with st.expander(qn):
                st.write(a)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Additional Resources")
    RES = {
        "User Manual": ("📖", "ic-purple", "Comprehensive guide to all features.",
            "**SmartRFP User Manual**\n\n"
            "- **Upload** — add a PDF/DOCX/TXT RFP and start analysis.\n"
            "- **Dashboard** — track pipeline metrics, status mix and recent RFPs.\n"
            "- **Resource Cost** — view the cost estimate, role breakdown and allocation.\n"
            "- **Human Review** — approve, edit, comment or regenerate each section.\n"
            "- **Export** — download the proposal as PDF, Word, Excel, HTML or text.\n"
            "- **Settings** — preferences, Groq model and local data management."),
        "Video Tutorials": ("▶️", "ic-amber", "Step-by-step walkthroughs.",
            "**Guided walkthrough**\n\n"
            "1. Upload an RFP and click *Analyze & Generate Response*.\n"
            "2. Watch the pipeline run (parse → RAG + pricing → synthesis).\n"
            "3. Open *Human Review*, approve or edit sections.\n"
            "4. Go to *Export* and download in your chosen format.\n\n"
            "Each step in the app mirrors this sequence end to end."),
        "Templates": ("📄", "ic-green", "Sample RFP templates & best practices.",
            "**Best-practice RFP structure**\n\n"
            "- Functional Requirements\n- Non-Functional Requirements\n"
            "- Compliance & Security\n- Commercial / Pricing line items\n\n"
            "Clear, sectioned RFPs produce the most accurate extraction and drafts. "
            "The bundled sample RFPs (Healthcare, Cloud Migration, Core Banking) follow this layout."),
        "Release Notes": ("🆕", "ic-blue", "Latest features and improvements.",
            "**Latest updates**\n\n"
            "- Demo data now seeds only once — deleting all RFPs keeps the dashboard empty.\n"
            "- Cards use real bordered containers, so tables and delete buttons sit inside the box.\n"
            "- Donut shows count and percent; Resource Cost has a role filter.\n"
            "- Export adds a Text (TXT) format and uniform format cards.\n"
            "- Help guides, knowledge base and these resources are fully interactive."),
    }
    ss.setdefault("help_res", None)
    rc = st.columns(4)
    for i, (name, (e, ic, desc, body)) in enumerate(RES.items()):
        with rc[i]:
            st.markdown(f"<div class='helpcard'><div class='ic {ic}'>{e}</div><div class='t'>{name}</div>"
                        f"<div class='d'>{desc}</div></div>", unsafe_allow_html=True)
            label = "✕ Close" if ss.help_res == name else "Open →"
            if st.button(label, key=f"res_{name}", use_container_width=True):
                ss.help_res = None if ss.help_res == name else name
                st.rerun()
    if ss.help_res:
        with card(f"{RES[ss.help_res][0]} {ss.help_res}"):
            st.markdown(RES[ss.help_res][3])

