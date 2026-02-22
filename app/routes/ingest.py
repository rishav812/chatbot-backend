import io
import os
from datetime import datetime
from pypdf import PdfReader

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import Document
from app.services.s3_service import upload_pdf, download_pdf, list_pdfs

router = APIRouter(
    prefix="/api/ingest",
    tags=["ingest"]
)

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}


# Response models
class IngestResponse(BaseModel):
    status: str
    message: str
    data: dict


class DocumentOut(BaseModel):
    id: str
    title: str
    source: str | None
    doc_type: str | None
    created_at: str
    updated_at: str


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    request: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF document and store its metadata in the documents table.
    """
    # Validate file extension
    file_ext = os.path.splitext(request.filename or "")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are allowed. Got: {file_ext or 'unknown'}",
        )

    # Read file contents
    contents = await request.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB",
        )

    # Upload PDF to S3
    file_name = request.filename or "untitled.pdf"
    try:
        s3_key = upload_pdf(contents, file_name)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save metadata to the documents table
    now = datetime.utcnow()
    document = Document(
        title=file_name,
        source=s3_key,
        doc_type=request.content_type or "application/pdf",
        created_at=now,
        updated_at=now,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return IngestResponse(
        status="success",
        message="PDF uploaded to S3 and saved to database",
        data={
            "id": str(document.id),
            "title": document.title,
            "source": document.source,
            "doc_type": document.doc_type,
            "file_size_bytes": file_size,
            "s3_key": s3_key,
            "created_at": document.created_at.isoformat(),
        },
    )


@router.get("/documents/{file_name}")
async def get_document(file_name: str):
    """
    Download a PDF from S3 and return its extracted text content.
    """
    try:
        pdf_bytes = download_pdf(file_name)
    except RuntimeError as e:
        return HTTPException(status_code=404, detail=str(e))

    # Extract text from PDF

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "content": text})
    
    print("pages>>>",pages)

    return {
        "file_name": file_name,
        "total_pages": len(reader.pages),
        "pages": pages,
    }


@router.get("/documents")
async def list_documents():
    """List all files in the S3 bucket."""
    try:
        files = list_pdfs()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"files": files}
