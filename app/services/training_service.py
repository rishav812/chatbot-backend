import io
import uuid
import asyncio
from datetime import datetime
from typing import List

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from app.database.session import AsyncSessionLocal
from app.database.models import DocumentChunk, ChunkEmbedding
from dotenv import load_dotenv
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


# Initialize once at module level
embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.environ["OPENAI_API_KEY"], 
)


async def save_chunks_to_db(
    chunks: List[str],
    document_id: uuid.UUID,
) -> List[DocumentChunk]:
    """Save raw text chunks to the document_chunks table."""
    now = datetime.utcnow()
    chunk_rows = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            content=chunk,
            created_at=now,
        )
        for i, chunk in enumerate(chunks)
    ]

    async with AsyncSessionLocal() as session:
        try:
            session.add_all(chunk_rows)
            await session.commit()
            print(f"save_chunks_to_db: saved {len(chunk_rows)} chunks")
        except Exception as e:
            await session.rollback()
            print(f"save_chunks_to_db: DB error – {e}")
            raise
    return chunk_rows


async def save_embeddings_to_db(
    chunk_rows: List[DocumentChunk],
    embeddings: List[List[float]],
) -> None:
    """Save embeddings for document chunks."""
    embedding_rows = [
        ChunkEmbedding(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            embedding=emb,
            embedding_model="text-embedding-3-small",
        )
        for chunk, emb in zip(chunk_rows, embeddings)
    ]
    async with AsyncSessionLocal() as session:
        try:
            session.add_all(embedding_rows)
            await session.commit()
            print(f"save_embeddings_to_db: saved {len(embedding_rows)} embeddings")
        except Exception as e:
            await session.rollback()
            print(f"save_embeddings_to_db: DB error – {e}")
            raise


async def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    """Generate embeddings for chunks using OpenAI."""
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None,
        embedding_model.embed_documents,
        chunks,
    )
    print(f"generate_embeddings: embedded {len(embeddings)} chunks")
    return embeddings


# async def embed_query(query: str) -> List[float]:
#     """Embed a single user query for similarity search."""
#     loop = asyncio.get_event_loop()
#     return await loop.run_in_executor(
#         None,
#         embedding_model.embed_query,
#         query,
#     )


async def bot_training(file_bytes: bytes, file_name: str, document_id: uuid.UUID) -> None:
    """
    Extract text from a PDF, split it into chunks, and persist each chunk
    to the document_chunks table linked to the given document_id.
    """
    try:
        # --- 1. Extract text ---
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text: list[str] = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(pages_text)

        # --- 2. Split into chunks ---
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(full_text)
        print(f"bot_training: {len(chunks)} chunks produced for '{file_name}'")

        # --- 3. Save chunks + generate embeddings in parallel ---
        db_task = save_chunks_to_db(chunks, document_id)
        embed_task = generate_embeddings(chunks)

        chunk_rows, embeddings = await asyncio.gather(db_task, embed_task)

        # --- 4. Store embeddings in pgvector ---
        await save_embeddings_to_db(chunk_rows, embeddings)
        print(f"bot_training: pipeline complete – {len(embeddings)} embeddings ready and saved via pgvector")

    except Exception as e:
        print(f"bot_training: error processing '{file_name}' – {e}")
        raise