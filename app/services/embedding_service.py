"""
Embedding insert + cosine similarity search using pgvector.
Relies on the existing async engine in app.database.session.
"""

import uuid
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ChunkEmbedding, DocumentChunk


# ─────────────────────────────────────────────
# INSERT
# ─────────────────────────────────────────────

async def insert_embedding(
    db: AsyncSession,
    chunk_id: uuid.UUID,
    embedding: list[float],
    model: str = "text-embedding-3-small",
) -> ChunkEmbedding:
    """Persist a vector embedding for a document chunk."""
    row = ChunkEmbedding(
        id=uuid.uuid4(),
        chunk_id=chunk_id,
        embedding=embedding,
        embedding_model=model,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ─────────────────────────────────────────────
# COSINE SIMILARITY SEARCH
# ─────────────────────────────────────────────

async def similarity_search(
    db: AsyncSession,
    query_embedding: list[float],
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict]:
    """
    Return the top-k document chunks closest to query_embedding
    using cosine distance (lower = more similar, so we flip to score).

    Returns a list of dicts with keys: chunk_id, content, score.
    """
    # pgvector cosine distance operator: <=>
    # score = 1 - cosine_distance  (1.0 = identical, 0.0 = orthogonal)
    stmt = text(
        """
        SELECT
            dc.id         AS chunk_id,
            dc.content    AS content,
            1 - (ce.embedding <=> CAST(:vec AS vector)) AS score
        FROM chunk_embeddings ce
        JOIN document_chunks  dc ON dc.id = ce.chunk_id
        WHERE 1 - (ce.embedding <=> CAST(:vec AS vector)) >= :min_score
        ORDER BY ce.embedding <=> CAST(:vec AS vector)
        LIMIT :top_k
        """
    )

    result = await db.execute(
        stmt,
        {
            "vec": str(query_embedding),   # pgvector accepts '[0.1,0.2,...]' string
            "top_k": top_k,
            "min_score": min_score,
        },
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]
