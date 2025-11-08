-- Enable pgvector (once per database)
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents you ingest (registry)
CREATE TABLE IF NOT EXISTS document (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  source TEXT,                -- "pdf", "docx"
  subject TEXT,
  tags TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Chunk store with embeddings (RAG index)
-- Use 3072 for text-embedding-3-large. If you use -small, set 1536.
CREATE TABLE IF NOT EXISTS doc_chunk (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
  page INT,
  chunk_index INT,
  text TEXT NOT NULL,
  meta JSONB,
  embedding vector(3072)
);

-- HNSW index (PG16+) for cosine search. If you’re on PG15, use IVFFLAT (needs REINDEX).
CREATE INDEX IF NOT EXISTS idx_doc_chunk_hnsw ON doc_chunk
USING hnsw (embedding vector_cosine_ops);

-- Helpful filters (optional)
CREATE INDEX IF NOT EXISTS idx_doc_chunk_meta_part ON doc_chunk ((meta->>'part_name'));
CREATE INDEX IF NOT EXISTS idx_doc_chunk_meta_scene ON doc_chunk ((meta->>'scene'));
