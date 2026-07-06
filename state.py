import streamlit as st
from config import GROQ_MODEL

ss = st.session_state
def initialize_state():
    # Fix note: this used to call seed_data.seed() and demo_seed.seed_demo_rfps()
    # here, which seeded a local SQLite database with knowledge-base docs and
    # demo RFPs every session. The backend now owns its own KB seeding
    # (see backend/main.py's startup hook, which seeds PostgreSQL AND embeds
    # into Pinecone) so this is no longer needed -- and would otherwise be
    # seeding a database the live app no longer reads from.
    if "booted" not in ss:
        ss.booted = True

    ss.setdefault("page", "Upload")
    ss.setdefault("current_rfp", None)
    ss.setdefault("export_format", "PDF")
    ss.setdefault("review_state", {})   # {f"{rid}:{section_id}": "Approved"/"In Review"/...}
    ss.setdefault("currency", "USD - US Dollar")
    ss.setdefault("items_per_page", 6)
    ss.setdefault("groq_model", GROQ_MODEL)
    ss.setdefault("workspace", "SmartRFP Solutions")
    ss.setdefault("theme", "Light")

def get_state():
    return ss