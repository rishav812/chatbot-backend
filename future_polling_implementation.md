# Background Task Status Polling (Option 1)

This document saves the blueprint for implementing real-time training status updates in the future.

## 1. Database Schema Update
Currently, `ingestion_runs` is defined in `tables.sql`, but we should use Alembic to add a `status` field to the `documents` table itself, or fully wire up `ingestion_runs`. 

If adding to `documents`:
```python
# app/database/models.py
class Document(Base):
    # ... existing fields
    status = Column(Text, default="Processing")  # "Processing", "Completed", "Failed"
    error_message = Column(Text, nullable=True)
```
Run `alembic revision --autogenerate -m "Add status to documents"` then `alembic upgrade head`.

## 2. Update `bot_training`
In `app/services/training_service.py`, update the document status when training finishes (or fails):
```python
async def bot_training(file_bytes: bytes, file_name: str, document_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        try:
            # --- 1. Extract text and Split ---
            # --- 2. Save chunks + generate embeddings ---
            # ... process normally ...

            # -> Success: Update DB status to Completed
            stmt = update(Document).where(Document.id == document_id).values(status="Completed")
            await session.execute(stmt)
            await session.commit()

        except Exception as e:
            # -> Failure: Update DB status to Failed
            stmt = update(Document).where(Document.id == document_id).values(
                status="Failed", error_message=str(e)
            )
            await session.execute(stmt)
            await session.commit()
            raise
```

## 3. Create a Status Polling Endpoint
In `app/routes/ingest.py`, add a simple GET endpoint so the frontend can ask for the status repeatedly:
```python
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException

@router.get("/status/{document_id}")
async def get_training_status(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {
        "document_id": doc.id,
        "status": doc.status,
        "error_message": doc.error_message
    }
```

## 4. Frontend Implementation
The frontend uploads a file, receives the `document.id`, and then runs a `setInterval` or `setTimeout` loop:
```javascript
// Pseudo-code
async function uploadAndPoll(file) {
    const uploadRes = await uploadFile(file); // Returns { data: { id: "123... " } }
    const docId = uploadRes.data.id;

    const interval = setInterval(async () => {
        const statusRes = await fetch(`/api/ingest/status/${docId}`);
        const json = await statusRes.json();
        
        if (json.status === "Completed") {
            clearInterval(interval);
            console.log("Chatbot training finished!");
        } else if (json.status === "Failed") {
            clearInterval(interval);
            console.error("Training failed: ", json.error_message);
        }
    }, 3000); // Ping every 3 seconds
}
```
