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
from ui import api
from config import APP_NAME
import state
from PIL import Image

logo = Image.open("ey-logo.png")

st.set_page_config(page_title=f"{APP_NAME} — RFP Analysis", page_icon=logo,
                   layout="wide", initial_sidebar_state="expanded")
state.initialize_state()
ss = state.get_state()

# =========================================================================== #
#  STYLES
# =========================================================================== #
st.markdown("""
<style>
:root{
  --yellow:#FACC15;
  --yellow2:#EAB308;
  --yellow-d:#CA8A04;
  --yellow-l:#EAB308;

  --ink:#FFFFFF;
  --ink2:#E5E5E5;
  --muted:#BFBFBF;

  --line:#2D2D2D;

  --green:#22C55E;
  --green-l:#16361F;

  --amber:#FACC15;
  --amber-l:#3A3100;

  --purple:#A855F7;
  --purple-l:#2D1B45;

  --teal:#14B8A6;
  --teal-l:#103D39;

  --red:#EF4444;
  --red-l:#3A1818;

  --bg:#0A0A0A;
}
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
.stApp{
    background:#0A0A0A;
    color:white;
}
.stMarkdown,
.stMarkdown p,
.stMarkdown li,
.stApp p,
.stApp li{
    color:#F5F5F5;
}
#MainMenu, header[data-testid="stHeader"] {background: transparent;border: none;}, footer{ visibility:hidden; }
.block-container{ padding-top:1.4rem; padding-bottom:3rem; max-width:1340px; }
/* fixed-height scrollable Sections list so it doesn't stretch the page */
.seclist{ max-height:430px; overflow-y:auto; padding-right:.2rem; }

/* Sidebar */
section[data-testid="stSidebar"]{ background:#111111; border-right:1px solid var(--line); width:265px!important; }
section[data-testid="stSidebar"] .block-container{ padding-top:1.1rem; }
.brand{ display:flex; align-items:center; gap:.6rem; padding:.1rem .3rem 1.2rem; }
.brand .logo{ font-size:1.7rem; }
.brand .name{ font-size:1.4rem; font-weight:800; color:var(--ink); line-height:1; }
.brand .name span{ color:var(--yellow); }
.brand .sub{ font-size:.7rem; color:var(--muted); margin-top:.18rem; }
section[data-testid="stSidebar"] .stButton>button{
  width:100%; text-align:left; justify-content:flex-start; background:#1A1A1A; color:#FACC15;
  border:1px solid transparent; border-radius:11px; padding:.6rem .85rem; font-weight:600;
  font-size:.97rem; box-shadow:none; transition:all .12s ease; margin-bottom:.18rem;
}
section[data-testid="stSidebar"] .stButton>button:hover{ background:var(--yellow-l); color:var(--yellow-d); }
section[data-testid="stSidebar"] .stButton>button:focus{ box-shadow:none; }
.nav-active>button{ background:var(--yellow-l)!important; color:var(--yellow)!important; font-weight:700!important; }
.groq{ margin-top:1rem; padding:.85rem .9rem; background:#171717; border:1px solid var(--line);
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
.chip{ display:inline-flex; align-items:center; gap:.45rem; background:#171717; border:1px solid var(--line);
  border-radius:11px; padding:.45rem .8rem; font-weight:600; color:var(--ink); font-size:.9rem; }
.avatar{ width:42px; height:42px; border-radius:50%; background:#171717; border:1px solid var(--line);
  display:flex; align-items:center; justify-content:center; font-size:1.15rem; margin-left:auto;
  box-shadow:0 1px 3px rgba(16,24,40,.05); }

/* Cards */
.card{ background:#171717; border:1px solid var(--line); border-radius:16px; padding:1.15rem 1.25rem;
  box-shadow:0 1px 3px rgba(16,24,40,.04); margin-bottom:1rem; }
.card h3{ font-size:1.05rem; font-weight:800; color:var(--ink); margin:0 0 .9rem; }
/* real st.container(border=True) styled as a card so widgets sit inside it */
div[data-testid="stVerticalBlockBorderWrapper"]{ background:#171717; border:1px solid var(--line)!important;
  border-radius:16px; box-shadow:0 1px 3px rgba(16,24,40,.04); padding:.4rem .35rem; margin-bottom:.5rem; }
.cardtitle{ font-size:1.05rem; font-weight:800; color:var(--ink); margin:.15rem .25rem .7rem; }
.metric{ background:#171717; border:1px solid var(--line); border-radius:16px; padding:1.05rem 1.15rem; height:100%;
  box-shadow:0 1px 3px rgba(16,24,40,.04); }
.metric .top{ display:flex; justify-content:space-between; align-items:flex-start; }
.metric .lab{ color:var(--muted); font-weight:700; font-size:.82rem; }
.metric .val{ font-size:1.95rem; font-weight:800; color:var(--ink); line-height:1.1; margin-top:.35rem; }
.metric .sub{ color:var(--muted); font-size:.76rem; margin-top:.25rem; }
.ic{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:1.2rem; }
.ic-blue{ background:var(--yellow-l); } .ic-green{ background:var(--green-l); } .ic-amber{ background:var(--amber-l); }
.ic-purple{ background:var(--purple-l); } .ic-teal{ background:var(--teal-l); } .ic-red{ background:var(--red-l); }

/* Expander header */
[data-testid="stExpander"] details summary {
    background: #171717 !important;
    color: #F5F5F5 !important;
    border: 1px solid var(--line);
    border-radius: 10px;
}

/* Expanded content */
[data-testid="stExpander"] details[open] > div {
    background: #171717 !important;
    color: #F5F5F5 !important;
}

/* Any markdown/text inside */
[data-testid="stExpander"] * {
    color: #F5F5F5 !important;
}

/* Pills */
.pill{ display:inline-block; padding:.16rem .6rem; border-radius:999px; font-size:.74rem; font-weight:700; }
.p-rev{ background:var(--amber-l); color:#b45309; } .p-ana{ background:var(--yellow-l); color:var(--yellow); }
.p-app{ background:var(--green-l); color:#15803d; } .p-exp{ background:var(--teal-l); color:#0f766e; }
.p-pend{ background:#2a2a2a; color:#BFBFBF; } .p-rej{ background:var(--red-l); color:#b91c1c; }

/* All Streamlit buttons */
div.stButton > button {
    background-color: #3A3A3A !important;
    color: #fff !important;
    border: 1px solid #FACC15 !important;
}

/* Hover */
div.stButton > button:hover {
    background-color: #EAB308 !important;
    color: #fff !important;
    border-color: #EAB308 !important;
}

/* Focus */
div.stButton > button:focus,
div.stButton > button:active {
    background-color: #EAB308 !important;
    color: #fff !important;
    border-color: #EAB308 !important;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background-color: #3A3A3A !important;
    border-color: #FACC15 !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: #EAB308 !important;
    border-color: #EAB308 !important;
}

.stButton > button:disabled {
    background-color: #3A3A3A !important;
    color: #7a7a7a !important;
    border-color: #555555 !important;
    cursor: not-allowed;
    opacity: 1 !important;   /* Prevent Streamlit from making it look faded */
}

/* Download button */
.stDownloadButton > button {
    background-color: #FACC15 !important;
    border-color: #FACC15 !important;
    color: white !important;
}

.stDownloadButton > button:hover {
    background-color: #EAB308 !important;
    border-color: #EAB308 !important;
    color: white !important;
}

.stDownloadButton > button:disabled {
    background-color: #3A3A3A !important;
    border-color: #555555 !important;
    color: #7a7a7a !important;
    cursor: not-allowed;
    opacity: 1 !important;
}

/* small bits */
.muted{ color:var(--muted); } .b{ font-weight:700; color:var(--ink); }
.refpill{ display:inline-block; background:var(--yellow-l); color:var(--yellow-d); border:1px solid #FACC15;
  border-radius:8px; padding:.2rem .55rem; font-size:.78rem; margin:.15rem .25rem .15rem 0; }
hr{ border:none; border-top:1px solid var(--line); margin:1rem 0; }
.fmtcard{ border:1px solid var(--line); border-radius:14px; padding:1rem .6rem; text-align:center; background:#171717;
  min-height:142px; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; }
.fmtcard.sel{ border:2px solid var(--yellow); background:#252000; }
.fmtcard .e{ font-size:1.7rem; } .fmtcard .t{ font-weight:800; color:var(--ink); margin-top:.3rem; font-size:.92rem; }
.fmtcard .d{ color:var(--muted); font-size:.74rem; margin-top:.25rem; line-height:1.3; }
.feed{ display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid var(--line); }
.feed .fi{ width:34px; height:34px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:1rem; }
.feed .ft{ font-weight:600; color:var(--ink2); font-size:.9rem; } .feed .fd{ color:var(--muted); font-size:.78rem; }
.step{ text-align:center; } .step .c{ width:46px; height:46px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; margin:0 auto; font-size:1.2rem; border:2px solid var(--line); background:#171717; }
.step .c.done{ background:var(--green-l); border-color:#22C55E; } .step .c.prog{ background:var(--yellow-l); border-color:#FACC15; }
.step .n{ font-weight:700; color:var(--ink); font-size:.82rem; margin-top:.35rem; }
.step .s{ font-size:.72rem; } .arrow{ color:#FACC15; font-size:1.3rem; text-align:center; padding-top:.7rem; }
.helpcard{ background:#171717; border:1px solid var(--line); border-radius:14px; padding:1.1rem; height:100%; }
.helpcard .e{ width:46px;height:46px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;}
.helpcard .t{ font-weight:800; color:var(--ink); margin-top:.6rem; } .helpcard .d{ color:var(--muted); font-size:.82rem; margin:.3rem 0 .5rem; }
div[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:12px; }
[data-testid="stFileUploaderDropzone"]{ background:#171717; border:2px dashed #FACC15; border-radius:16px; padding:2rem; }
.stButton>button{ border-radius:10px; font-weight:600; color: #171717 !important; }
[data-testid="stFileUploader"] button{
    background:#FACC15 !important;
    color:#000 !important;
    border:1px solid #FACC15 !important;
    border-radius:10px !important;
    font-weight:700 !important;
}

[data-testid="stFileUploader"] button:hover{
    background:#EAB308 !important;
    border-color:#EAB308 !important;
    color:#000 !important;
}
</style>
""", unsafe_allow_html=True)

if ss.get("theme") == "Dark":
    st.markdown("""
    <style>
    .stApp{ background:#0b1220 !important; color:#e5e7eb !important; }
    section[data-testid="stSidebar"]{ background:#0f172a !important; border-color:#1f2a44 !important; }
    .card,.metric,.helpcard,.fmtcard,
    div[data-testid="stVerticalBlockBorderWrapper"]{ background:#1e293b !important; border-color:#334155 !important; }
    .cardtitle,.card h3,.tb h1,.metric .val,.b,.brand .name{ color:#f8fafc !important; }
    .stMarkdown,.stMarkdown p,.stMarkdown li,.stApp p,.stApp li,.stApp span,
    .stApp label,.metric .lab,.muted{ color:#FACC15 !important; }
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
    st.markdown(
                f"""
                <div class="brand">
                    <img src="ey_logo.png" class="logo" alt="EY Logo">
                    <div>
                        <div class="name">Smart<span>RFP</span></div>
                        <div class="sub">{ss.get('workspace', 'AI-Powered RFP Analysis')}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True)
    for name, icon in NAV:
        wrap = "nav-active" if ss.page == name else "nav-x"
        st.markdown(f"<div class='{wrap}'>", unsafe_allow_html=True)
        if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
            go(name)
        st.markdown("</div>", unsafe_allow_html=True)

    llm_status = api.llm_status()
    live = bool()
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