-- PostgreSQL + pgvector DDL Specification
-- Canonical Schema for The Lenny Growth Assistant

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Episodes Metadata
CREATE TABLE IF NOT EXISTS episodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(512) NOT NULL,
    guest VARCHAR(256) NOT NULL,
    publication_date DATE,
    source_path VARCHAR(1024) NOT NULL UNIQUE,
    episode_url VARCHAR(1024),
    youtube_url VARCHAR(1024),
    description TEXT,
    video_id VARCHAR(64),
    duration_seconds NUMERIC,
    duration VARCHAR(32),
    view_count INT,
    channel VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backward-compatible schema evolution for existing deployments
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS video_id VARCHAR(64);
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS duration_seconds NUMERIC;
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS duration VARCHAR(32);
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS view_count INT;
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS channel VARCHAR(256);

-- Transcript Chunks & Embeddings
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    speaker VARCHAR(256),
    content TEXT NOT NULL,
    embedding VECTOR(768), -- Fixed 768-dim via nomic-embed-text (never changes with LLM_PROVIDER)
    content_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_chunk_hash UNIQUE(content_hash)
);

CREATE INDEX IF NOT EXISTS idx_chunks_episode_id ON transcript_chunks(episode_id);

-- HNSW Index for sub-25ms Cosine Similarity Search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON transcript_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(256) NOT NULL DEFAULT 'New Research Session',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    evidence_tier VARCHAR(32), -- 'strong', 'limited', 'conflicting', 'insufficient'
    latency_ms INT,
    model_used VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, created_at ASC);

-- Source References (Provenance Tracking)
CREATE TABLE IF NOT EXISTS source_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES transcript_chunks(id) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL,
    quoted_excerpt TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artifacts
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    artifact_type VARCHAR(64) NOT NULL, -- 'markdown', 'ship30_essay', 'html_card'
    title VARCHAR(512) NOT NULL,
    content_raw TEXT NOT NULL,
    content_html TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
