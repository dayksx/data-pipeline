-- Enable the extension (do this once in each database where you want to use it)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.rag_chunks (
    id          SERIAL PRIMARY KEY,
    chunk_id    TEXT NOT NULL UNIQUE,          -- hash source+section (idempotence)
    source      TEXT NOT NULL,                 -- nom du fichier .md
    section     TEXT NOT NULL,                 -- titre ## 
    content     TEXT NOT NULL,
    embedding   vector(1536) NOT NULL,         -- text-embedding-3-small
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index: create after `insights index` once the table has rows (lists must be < row count).