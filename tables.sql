
-- ================================
-- RAG Ingestion Schema (Neon + pgvector)
-- ================================

-- Enable pgvector (run once)
CREATE EXTENSION IF NOT EXISTS vector;
  
-- ----------------
-- Documents table
-- ----------------
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  source TEXT,
  doc_type TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- -----------------------
-- Document chunks table
-- -----------------------
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  -- chunk_index INT,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

-- -------------------------
-- Chunk embeddings table
-- -------------------------
CREATE TABLE IF NOT EXISTS chunk_embeddings (
  id UUID PRIMARY KEY,
  chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
  embedding VECTOR(1536),
  embedding_model TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- -------------------------
-- Ingestion runs (optional)
-- -------------------------
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id UUID PRIMARY KEY,
  status TEXT,
  error TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- -------------------------
-- Indexes
-- -------------------------
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
ON chunk_embeddings
USING hnsw (embedding vector_cosine_ops);

