/*
# Create Mutual Fund RAG Chatbot Schema

## Overview
This migration creates the database schema for a Facts-Only Mutual Fund RAG chatbot.
It stores ingested AMC/SEBI/AMFI source documents, their text chunks, and OpenAI
embeddings (1536-dim text-embedding-3-small) for semantic search. An RPC function
performs vector similarity search to retrieve relevant chunks for grounded LLM answers.

## 1. Extensions
- `vector` (pgvector): enables the `vector` column type for storing embeddings.

## 2. New Tables
- `fund_sources`: Metadata about each official source document (AMC, SEBI, AMFI).
  - `id` (uuid PK)
  - `source_id` (text, unique — short identifier like "hdfc-balanced-factsheet")
  - `amc` (text — Asset Management Company name)
  - `scheme_name` (text — mutual fund scheme name)
  - `source_type` (text — 'factsheet' | 'scheme_information' | 'sebi_circular' | 'amfi_data')
  - `url` (text — official URL)
  - `title` (text — document title)
  - `ingested_at` (timestamptz — when document was ingested)
  - `last_updated` (date — date of the source document's latest content)

- `fund_chunks`: Text chunks extracted from source documents for RAG.
  - `id` (uuid PK)
  - `source_id` (text FK → fund_sources.source_id)
  - `chunk_index` (int — ordinal position within the source document)
  - `content` (text — the chunk text)
  - `embedding` (vector(1536) — OpenAI text-embedding-3-small)
  - `metadata` (jsonb — flexible metadata: section, page, facts, etc.)
  - `created_at` (timestamptz)

## 3. RPC Functions
- `match_fund_chunks`: Semantic search function that takes a query embedding vector
  and returns the top-N most similar chunks with similarity score, filtered by
  optional source_id or scheme_name. Uses pgvector cosine distance operator.

## 4. Security
- RLS enabled on both tables.
- This is a no-auth (single-tenant) app: the chatbot frontend uses the anon key.
- Policies allow anon + authenticated to read (SELECT) both tables.
- INSERT/UPDATE/DELETE restricted to authenticated (backend ingestion only).
*/

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ── fund_sources ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fund_sources (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id   text UNIQUE NOT NULL,
  amc         text NOT NULL,
  scheme_name text,
  source_type text NOT NULL,
  url         text NOT NULL,
  title       text NOT NULL,
  ingested_at timestamptz DEFAULT now(),
  last_updated date
);

ALTER TABLE fund_sources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_fund_sources" ON fund_sources;
CREATE POLICY "anon_read_fund_sources" ON fund_sources FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "auth_insert_fund_sources" ON fund_sources;
CREATE POLICY "auth_insert_fund_sources" ON fund_sources FOR INSERT
  TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "auth_update_fund_sources" ON fund_sources;
CREATE POLICY "auth_update_fund_sources" ON fund_sources FOR UPDATE
  TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "auth_delete_fund_sources" ON fund_sources;
CREATE POLICY "auth_delete_fund_sources" ON fund_sources FOR DELETE
  TO authenticated USING (true);

-- ── fund_chunks ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fund_chunks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id   text NOT NULL REFERENCES fund_sources(source_id) ON DELETE CASCADE,
  chunk_index int NOT NULL,
  content     text NOT NULL,
  embedding   vector(1536),
  metadata    jsonb DEFAULT '{}'::jsonb,
  created_at  timestamptz DEFAULT now()
);

ALTER TABLE fund_chunks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_fund_chunks" ON fund_chunks;
CREATE POLICY "anon_read_fund_chunks" ON fund_chunks FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "auth_insert_fund_chunks" ON fund_chunks;
CREATE POLICY "auth_insert_fund_chunks" ON fund_chunks FOR INSERT
  TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "auth_update_fund_chunks" ON fund_chunks;
CREATE POLICY "auth_update_fund_chunks" ON fund_chunks FOR UPDATE
  TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "auth_delete_fund_chunks" ON fund_chunks;
CREATE POLICY "auth_delete_fund_chunks" ON fund_chunks FOR DELETE
  TO authenticated USING (true);

-- Index for faster vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS fund_chunks_embedding_idx
  ON fund_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Index for filtering by source_id
CREATE INDEX IF NOT EXISTS fund_chunks_source_id_idx ON fund_chunks (source_id);

-- ── match_fund_chunks RPC ─────────────────────────────────────
CREATE OR REPLACE FUNCTION match_fund_chunks(
  query_embedding vector(1536),
  match_count    int DEFAULT 5,
  filter_source  text DEFAULT NULL,
  filter_scheme  text DEFAULT NULL
)
RETURNS TABLE (
  id          uuid,
  source_id   text,
  chunk_index int,
  content     text,
  metadata    jsonb,
  similarity  float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.source_id,
    c.chunk_index,
    c.content,
    c.metadata,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM fund_chunks c
  JOIN fund_sources s ON c.source_id = s.source_id
  WHERE c.embedding IS NOT NULL
    AND (filter_source IS NULL OR c.source_id = filter_source)
    AND (filter_scheme IS NULL OR s.scheme_name = filter_scheme)
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
$$;
