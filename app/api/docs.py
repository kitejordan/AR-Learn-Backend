from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from tempfile import NamedTemporaryFile
import shutil
from app.managers.document_ingest_pg import ingest_pdf_to_pg

router = APIRouter(prefix="/docs", tags=["docs"])

@router.post("/ingest-pdf")
def ingest_pdf(
    file: UploadFile = File(...),
    model_id: str | None = Query(None),
    model_name: str | None = Query(None),
    subject: str | None = Query(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF supported.")

    with NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp.flush()
        res = ingest_pdf_to_pg(
            tmp.name,
            title=file.filename,
            subject=subject,
            model_id=model_id,
            model_name=model_name,
        )
    return res
