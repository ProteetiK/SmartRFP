import requests

#API_BASE_URL = "http://backend:8000"
import streamlit as st
BASE_URL = st.secrets["BACKEND_URL"]

def upload_rfp(
    uploaded_file,
    deal_name="",
    client_name="",
    region="",
    deadline="",
    assigned_role="",
    use_web_search=True,
):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }

    data = {
        "deal_name": deal_name,
        "client_name": client_name,
        "region": region,
        "deadline": deadline,
        "assigned_role": assigned_role,
        "use_web_search": str(use_web_search).lower(),
    }

    response = requests.post(
        f"{API_BASE_URL}/upload-rfp",
        files=files,
        data=data,
    )

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    response.raise_for_status()

    return response.json()

def regenerate(rfp_id):
    response = requests.post(
        f"{API_BASE_URL}/regenerate/{rfp_id}"
    )
    response.raise_for_status()
    return response.json()

