create extension if not exists vector;

create table if not exists document (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  source text,
  subject text,
  tags text[],
  created_at timestamptz default now()
);

create table if not exists doc_chunk (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references document(id) on delete cascade,
  page int,
  chunk_index int,
  text text not null,
  meta jsonb,
  embedding vector(1536)  -- 3-small
);

create index if not exists idx_doc_chunk_hnsw
on doc_chunk
using hnsw (embedding vector_cosine_ops);

create index if not exists idx_doc_chunk_meta_part
on doc_chunk ((meta->>'part_name'));

create index if not exists idx_doc_chunk_meta_scene
on doc_chunk ((meta->>'scene'));

create index if not exists idx_doc_chunk_meta_model
on doc_chunk ((meta->>'model_id'));
