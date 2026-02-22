import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import Document

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

    # Create a new Document record
    now = datetime.utcnow()
    document = Document(
        title=request.filename or "untitled.pdf",
        source=request.filename,
        doc_type=request.content_type or "application/pdf",
        created_at=now,
        updated_at=now,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return IngestResponse(
        status="success",
        message="Document uploaded and saved to database",
        data={
            "id": str(document.id),
            "title": document.title,
            "source": document.source,
            "doc_type": document.doc_type,
            "file_size_bytes": file_size,
            "created_at": document.created_at.isoformat(),
        },
    )
