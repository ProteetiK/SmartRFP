import streamlit as st
import base64
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

@st.cache_resource
def load_logo():
    return Image.open("ey-logo.png")

logo = load_logo()

st.set_page_config(page_title=f"{APP_NAME} — RFP Analysis", page_icon=logo,
                   layout="wide", initial_sidebar_state="expanded")
state.initialize_state()
ss = state.get_state()

# =========================================================================== #
#  STYLES
# =========================================================================== #
from pathlib import Path

@st.cache_resource
def load_css():
    from pathlib import Path
    return Path("styles.css").read_text()

st.markdown(
    f"<style>{load_css()}</style>",
    unsafe_allow_html=True,
)

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
    def get_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    logo = get_base64("ey-logo-dark.png")
    st.markdown(
                f"""
                <div class="brand">
                    <div class="logo-box">
                        <img src="data:image/png;base64,{logo}">
                    </div>
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

    @st.cache_data(ttl=60)
    def cached_llm_status():
        return api.llm_status()

    llm_status = cached_llm_status()
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