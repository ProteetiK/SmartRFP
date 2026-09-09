from fastapi import UploadFile

from backend.database import SessionLocal
from backend import crud
from backend.utils.file_handler import extract_text
from backend.pipeline import run_pipeline


async def analyze_rfp(file: UploadFile, deal_name: str = "", client_name: str = "",
                      region: str = "", deadline: str = "", assigned_role: str = "",
                      use_web_search: bool = True):
    contents = await file.read()
    raw_text = extract_text(file.filename, contents)

    db = SessionLocal()
    try:
        rfp_id = crud.create_rfp(
            db, deal_name=deal_name or file.filename, client_name=client_name,
            region=region, deadline=deadline, contact_email="", notes="",
            file_name=file.filename, raw_text=raw_text, assigned_role=assigned_role,
            assigned_to="", use_web_search=use_web_search)

        result = run_pipeline(db, rfp_id=rfp_id, raw_text=raw_text,
                              filename=file.filename, use_web_search=use_web_search)
        return {"success": True, "rfp_id": rfp_id, "result": result}
    finally:
        db.close()


def regenerate_pipeline(rfp_id: int):
    db = SessionLocal()
    try:
        rfp = crud.get_rfp_obj(db, rfp_id)
        if not rfp:
            return {"success": False, "message": "RFP not found"}
        run_pipeline(db, rfp_id=rfp.id, raw_text=rfp.raw_text,
                     filename=rfp.file_name or f"rfp_{rfp.id}",
                     use_web_search=bool(rfp.use_web_search))
        crud.log_action(db, rfp.id, "Draft Regenerated", "System")
        return {"success": True, "message": "Draft regenerated"}
    finally:
        db.close()


def human_review(rfp_id: int, status: str, comments: str = ""):
    db = SessionLocal()
    try:
        crud.update_rfp_status(db, rfp_id, status)
        crud.log_action(db, rfp_id, "Human Review", "Reviewer", comments or status)
        return {"success": True, "status": status}
    finally:
        db.close()
