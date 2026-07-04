"""
app.py — SmartRFP
=================
Streamlit front end styled to match the SmartRFP design mockups:
Upload, Dashboard, Resource Cost, Human Review, Export, Settings, Help & Docs.

This is a pure HTTP client of the FastAPI backend (see ui/api.py) --
PostgreSQL, Pinecone, and the Groq/OpenAI LLM calls all live server-side.
The frontend holds no database connection and no LLM API keys.
"""
import streamlit as st

from ui.dashboard import page_dashboard
from ui.export import page_export
from ui.resource_cost import page_resource_cost
from ui.review import page_review
from ui.settings import page_settings
from ui.upload import page_upload
from ui.llm_eval import page_llm_eval
from ui.help_pg import page_help
from ui.ui_utils import go
from ui import api

from config import APP_NAME
import state

st.set_page_config(page_title=f"{APP_NAME} — RFP Analysis", page_icon="📄",
                   layout="wide", initial_sidebar_state="expanded")
state.initialize_state()
ss = state.get_state()

# =========================================================================== #
#  STYLES
# =========================================================================== #
st.markdown("""
<style>
:root{
  --blue:#2563eb; --blue2:#3b82f6; --blue-d:#1d4ed8; --blue-l:#eaf1ff;
  --ink:#000000; --ink2:#111111; --muted:#333333; --line:#e8edf3;
  --green:#16a34a; --green-l:#e7f7ee; --amber:#d97706; --amber-l:#fff5e6;
  --purple:#7c3aed; --purple-l:#f1ecfe; --teal:#0d9488; --teal-l:#e3f7f4;
  --red:#dc2626; --red-l:#fdeced;
  --bg: linear-gradient(
    135deg,
    #ffffff 0%,
    #f8feff 20%,
    #f3fefe 50%,
    #e9fcfd 75%,
    #ddfbfd 100%
);
}
/* Body text → Arial; headings → Calibri */
html, body, .stApp, [class^="st-"], [class*=" st-"], .stMarkdown,
p, span, div, label, input, textarea, select, button, li, td, th {
  font-family: Arial, "Helvetica Neue", Helvetica, sans-serif !important;
}
h1, h2, h3, h4, h5, h6, .tb h1, .cardtitle, .card h3, .brand .name,
.metric .val, .helpcard .t, .fmtcard .t {
  font-family: Calibri, "Segoe UI", Candara, "Trebuchet MS", sans-serif !important;
}
/* …but NEVER override Streamlit's Material icon font (fixes the overlapping
   "keyboard_arrow_down" text on expanders, selects, etc.) */
[data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined,
[data-testid="stExpanderToggleIcon"], span[translate="no"] {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined",
               "Material Icons" !important;
}
.stApp{ background:var(--bg); color:#000; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stApp p, .stApp li { color:#000; }
#MainMenu, header[data-testid="stHeader"] {background: transparent;border: none;}, footer{ visibility:hidden; }
.block-container{ padding-top:1.4rem; padding-bottom:3rem; max-width:1340px; }
/* fixed-height scrollable Sections list so it doesn't stretch the page */
.seclist{ max-height:430px; overflow-y:auto; padding-right:.2rem; }

/* Sidebar */
section[data-testid="stSidebar"]{ background:#e3fcfd; border-right:1px solid var(--line); width:265px!important; }
section[data-testid="stSidebar"] .block-container{ padding-top:1.1rem; }
.brand{ display:flex; align-items:center; gap:.6rem; padding:.1rem .3rem 1.2rem; }
.brand .logo{ font-size:1.7rem; }
.brand .name{ font-size:1.4rem; font-weight:800; color:var(--ink); line-height:1; }
.brand .name span{ color:var(--blue); }
.brand .sub{ font-size:.7rem; color:var(--muted); margin-top:.18rem; }
section[data-testid="stSidebar"] .stButton>button{
  width:100%; text-align:left; justify-content:flex-start; background:#f6fefe; color:#fff;
  border:1px solid transparent; border-radius:11px; padding:.6rem .85rem; font-weight:600;
  font-size:.97rem; box-shadow:none; transition:all .12s ease; margin-bottom:.18rem;
}
section[data-testid="stSidebar"] .stButton>button:hover{ background:var(--blue-l); color:var(--blue-d); }
section[data-testid="stSidebar"] .stButton>button:focus{ box-shadow:none; }
.nav-active>button{ background:var(--blue-l)!important; color:var(--blue)!important; font-weight:700!important; }
.groq{ margin-top:1rem; padding:.85rem .9rem; background:#fff; border:1px solid var(--line);
  border-radius:14px; box-shadow:0 1px 3px rgba(16,24,40,.05); }
.groq .row{ display:flex; align-items:center; gap:.45rem; font-weight:700; color:var(--ink); font-size:.86rem; }
.groq .dot{ width:9px; height:9px; border-radius:50%; background:var(--green); box-shadow:0 0 0 3px var(--green-l); }
.groq .dot.off{ background:var(--amber); box-shadow:0 0 0 3px var(--amber-l); }
.groq .st{ color:var(--green); font-size:.8rem; margin:.2rem 0 .1rem; }
.groq .st.off{ color:var(--amber); }
.groq .mod{ color:var(--muted); font-size:.72rem; margin-bottom:.5rem; }

/* Top bar */
.tb{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem; }
.tb h1{ font-size:1.7rem; font-weight:800; color:var(--ink); margin:0; display:flex; align-items:center; gap:.5rem;}
.tb .sub{ color:var(--muted); font-size:.93rem; margin-top:.15rem; }
.chip{ display:inline-flex; align-items:center; gap:.45rem; background:#fff; border:1px solid var(--line);
  border-radius:11px; padding:.45rem .8rem; font-weight:600; color:var(--ink); font-size:.9rem; }
.avatar{ width:42px; height:42px; border-radius:50%; background:#fff; border:1px solid var(--line);
  display:flex; align-items:center; justify-content:center; font-size:1.15rem; margin-left:auto;
  box-shadow:0 1px 3px rgba(16,24,40,.05); }

/* Cards */
.card{ background:#dafbfd; border:1px solid var(--line); border-radius:16px; padding:1.15rem 1.25rem;
  box-shadow:0 1px 3px rgba(16,24,40,.04); margin-bottom:1rem; }
.card h3{ font-size:1.05rem; font-weight:800; color:var(--ink); margin:0 0 .9rem; }
/* real st.container(border=True) styled as a card so widgets sit inside it */
div[data-testid="stVerticalBlockBorderWrapper"]{ background:#fff; border:1px solid var(--line)!important;
  border-radius:16px; box-shadow:0 1px 3px rgba(16,24,40,.04); padding:.4rem .35rem; margin-bottom:.5rem; }
.cardtitle{ font-size:1.05rem; font-weight:800; color:var(--ink); margin:.15rem .25rem .7rem; }
.metric{ background:#dafbfd; border:1px solid var(--line); border-radius:16px; padding:1.05rem 1.15rem; height:100%;
  box-shadow:0 1px 3px rgba(16,24,40,.04); }
.metric .top{ display:flex; justify-content:space-between; align-items:flex-start; }
.metric .lab{ color:var(--muted); font-weight:700; font-size:.82rem; }
.metric .val{ font-size:1.95rem; font-weight:800; color:var(--ink); line-height:1.1; margin-top:.35rem; }
.metric .sub{ color:var(--muted); font-size:.76rem; margin-top:.25rem; }
.ic{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:1.2rem; }
.ic-blue{ background:var(--blue-l); } .ic-green{ background:var(--green-l); } .ic-amber{ background:var(--amber-l); }
.ic-purple{ background:var(--purple-l); } .ic-teal{ background:var(--teal-l); } .ic-red{ background:var(--red-l); }

/* Pills */
.pill{ display:inline-block; padding:.16rem .6rem; border-radius:999px; font-size:.74rem; font-weight:700; }
.p-rev{ background:var(--amber-l); color:#b45309; } .p-ana{ background:var(--blue-l); color:var(--blue); }
.p-app{ background:var(--green-l); color:#15803d; } .p-exp{ background:var(--teal-l); color:#0f766e; }
.p-pend{ background:#eef2f6; color:#64748b; } .p-rej{ background:var(--red-l); color:#b91c1c; }

/* Primary buttons */
.stButton > button[kind="primary"] {
    background-color: #B7EDF2 !important;
    border-color: #B7EDF2 !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: #A3E3E8 !important;
    border-color: #A3E3E8 !important;
}

.stButton > button:disabled {
    background-color: #d9ecee !important;
    color: #7a7a7a !important;
    border-color: #c9d9db !important;
    cursor: not-allowed;
    opacity: 1 !important;   /* Prevent Streamlit from making it look faded */
}

/* Download button */
.stDownloadButton > button {
    background-color: #B7EDF2 !important;
    border-color: #B7EDF2 !important;
    color: white !important;
}

.stDownloadButton > button:hover {
    background-color: #A3E3E8 !important;
    border-color: #A3E3E8 !important;
    color: white !important;
}

.stDownloadButton > button:disabled {
    background-color: #d9ecee !important;
    border-color: #c9d9db !important;
    color: #7a7a7a !important;
    cursor: not-allowed;
    opacity: 1 !important;
}

/* small bits */
.muted{ color:var(--muted); } .b{ font-weight:700; color:var(--ink); }
.refpill{ display:inline-block; background:var(--blue-l); color:var(--blue-d); border:1px solid #d6e4ff;
  border-radius:8px; padding:.2rem .55rem; font-size:.78rem; margin:.15rem .25rem .15rem 0; }
hr{ border:none; border-top:1px solid var(--line); margin:1rem 0; }
.fmtcard{ border:1px solid var(--line); border-radius:14px; padding:1rem .6rem; text-align:center; background:#fff;
  min-height:142px; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; }
.fmtcard.sel{ border:2px solid var(--blue); background:#f5f9ff; }
.fmtcard .e{ font-size:1.7rem; } .fmtcard .t{ font-weight:800; color:var(--ink); margin-top:.3rem; font-size:.92rem; }
.fmtcard .d{ color:var(--muted); font-size:.74rem; margin-top:.25rem; line-height:1.3; }
.feed{ display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid var(--line); }
.feed .fi{ width:34px; height:34px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:1rem; }
.feed .ft{ font-weight:600; color:var(--ink2); font-size:.9rem; } .feed .fd{ color:var(--muted); font-size:.78rem; }
.step{ text-align:center; } .step .c{ width:46px; height:46px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; margin:0 auto; font-size:1.2rem; border:2px solid var(--line); background:#fff; }
.step .c.done{ background:var(--green-l); border-color:#bbe7cc; } .step .c.prog{ background:var(--blue-l); border-color:#bcd4ff; }
.step .n{ font-weight:700; color:var(--ink); font-size:.82rem; margin-top:.35rem; }
.step .s{ font-size:.72rem; } .arrow{ color:#cbd5e1; font-size:1.3rem; text-align:center; padding-top:.7rem; }
.helpcard{ background:#dafbfd; border:1px solid var(--line); border-radius:14px; padding:1.1rem; height:100%; }
.helpcard .e{ width:46px;height:46px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;}
.helpcard .t{ font-weight:800; color:var(--ink); margin-top:.6rem; } .helpcard .d{ color:var(--muted); font-size:.82rem; margin:.3rem 0 .5rem; }
div[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:12px; }
[data-testid="stFileUploaderDropzone"]{ background:#fbfdff; border:2px dashed #bcd1f5; border-radius:16px; padding:2rem; }
.stButton>button{ border-radius:10px; font-weight:600; color: white !important; }
</style>
""", unsafe_allow_html=True)

# Dynamic theme (Settings → Application Preferences). Dark mode is opt-in; the
# default Light theme keeps the blue/white look with black text.
if ss.get("theme") == "Dark":
    st.markdown("""
    <style>
    .stApp{ background:#0b1220 !important; color:#e5e7eb !important; }
    section[data-testid="stSidebar"]{ background:#0f172a !important; border-color:#1f2a44 !important; }
    .card,.metric,.helpcard,.fmtcard,
    div[data-testid="stVerticalBlockBorderWrapper"]{ background:#1e293b !important; border-color:#334155 !important; }
    .cardtitle,.card h3,.tb h1,.metric .val,.b,.brand .name{ color:#f8fafc !important; }
    .stMarkdown,.stMarkdown p,.stMarkdown li,.stApp p,.stApp li,.stApp span,
    .stApp label,.metric .lab,.muted{ color:#cbd5e1 !important; }
    input,textarea,select,[data-baseweb="select"]>div{ background:#0f172a !important; color:#f1f5f9 !important; }
    .stDataFrame,div[data-testid="stDataFrame"]{ background:#1e293b !important; }
    </style>
    """, unsafe_allow_html=True)


# =========================================================================== #
#  SIDEBAR
# =========================================================================== #
NAV = [("Upload", "☁️"), ("Dashboard", "📊"), ("Resource Cost", "💲"),
       ("Human Review", "🗂️"), ("Export", "📤"), ("AI Evaluation", "🔎"), ("Settings", "⚙️"), ("Help & Docs", "❓")]

with st.sidebar:
    st.markdown(f"<div class='brand'><div class='logo'>📄</div><div>"
                f"<div class='name'>Smart<span>RFP</span></div>"
                f"<div class='sub'>{ss.get('workspace', 'AI-Powered RFP Analysis')}</div>"
                f"</div></div>", unsafe_allow_html=True)
    for name, icon in NAV:
        wrap = "nav-active" if ss.page == name else "nav-x"
        st.markdown(f"<div class='{wrap}'>", unsafe_allow_html=True)
        if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
            go(name)
        st.markdown("</div>", unsafe_allow_html=True)

    llm_status = api.llm_status()
    live = bool(llm_status.get("ok"))
    st.markdown(
        f"<div class='groq'><div class='row'><span class='dot {'' if live else 'off'}'></span>"
        f"Groq API Status</div><div class='st {'' if live else 'off'}'>"
        f"{'Connected' if live else 'Unavailable'}</div>"
        f"<div class='mod'>Model: {llm_status.get('model', '?')}</div></div>", unsafe_allow_html=True)
    if st.button("🔌 Test Connection", key="side_test", use_container_width=True):
        with st.spinner("Asking the backend to call Groq…"):
            r = api.llm_status()
        st.toast(("✅ " + r["message"]) if r.get("ok") else ("❌ " + r.get("message", "Unavailable")))

# =========================================================================== #
#  ROUTER
# =========================================================================== #
PAGES = {"Upload": page_upload, 
         "Dashboard": page_dashboard, 
         "Resource Cost": page_resource_cost,
         "Human Review": page_review, 
         "Export": page_export, 
         "AI Evaluation": page_llm_eval, 
         "Settings": page_settings,
         "Help & Docs": page_help}

PAGES.get(ss.page, page_dashboard)()