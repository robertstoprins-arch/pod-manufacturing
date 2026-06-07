import io
import os
import sys
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis as redis_lib

from app.db import get_db

router = APIRouter(tags=["system"])


@router.get("/debug/pdf-env")
def pdf_env():
    """Confirm PDF dependencies are available in the Render container."""
    result = {"python_version": sys.version}
    try:
        import reportlab
        result["reportlab"] = reportlab.Version
    except Exception as exc:
        result["reportlab"] = f"IMPORT ERROR: {exc}"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        result["reportlab_basic_imports"] = "ok"
    except Exception as exc:
        result["reportlab_basic_imports"] = f"ERROR: {exc}"
    result["cwd"] = os.getcwd()
    return result


@router.get("/debug/pdf-test")
def pdf_test():
    """Generate a minimal PDF — confirms ReportLab works end-to-end in Render."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("PDF Test — ReportLab OK", styles["Title"]),
            Spacer(1, 10 * mm),
            Paragraph("Hello from the Render PDF generator.", styles["Normal"]),
        ]
        doc.build(story)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="pdf-test.pdf"'},
        )
    except Exception as exc:
        import traceback
        return {"error": str(exc), "traceback": traceback.format_exc()}



@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    try:
        r = redis_lib.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2)
        r.ping()
        redis_status = "connected"
    except Exception as exc:
        redis_status = f"error: {exc}"

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"
    return {"status": overall, "db": db_status, "redis": redis_status}
