-- SessionManager PostgreSQL Schema
-- Multi-user LLM session & project management
-- Designed for: Langfuse integration, local JSONL tracking, LLM-powered naming/correlation

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Users / operators who create sessions
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT NOT NULL UNIQUE,          -- 'alex', 'irina'
    display_name    TEXT,
    email           TEXT UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    settings        JSONB DEFAULT '{}'             -- per-user prefs (default model, etc.)
);

-- Projects group related sessions
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,           -- 'xsolla-tool-catalog', 'neuronet'
    name            TEXT NOT NULL,                  -- 'Xsolla Tool Catalog'
    description     TEXT,
    owner_id        UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ,                   -- soft delete
    metadata        JSONB DEFAULT '{}'             -- git_repo, cwd, custom fields
);

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_slug ON projects(slug);

-- ============================================================================
-- SESSIONS
-- ============================================================================

-- A session = one conversation with an LLM
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT,                          -- original session ID from source tool
    user_id         UUID NOT NULL REFERENCES users(id),
    project_id      UUID REFERENCES projects(id),

    -- Source
    source          TEXT NOT NULL,                  -- 'claude-code', 'openclaw', 'codex', 'chatgpt'
    source_host     TEXT,                          -- hostname where session ran
    source_file     TEXT,                          -- original JSONL path

    -- Identity
    name            TEXT,                          -- human or LLM-generated name
    name_source     TEXT,                          -- 'manual', 'llm-auto', 'llm-user'
    description     TEXT,

    -- Model info
    model           TEXT,                          -- 'claude-sonnet-4-6', 'gpt-4o'
    provider        TEXT,                          -- 'anthropic-vertex', 'openai', 'anthropic'

    -- Timing
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    duration_ms     BIGINT GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (ended_at - started_at)) * 1000
    ) STORED,

    -- Stats
    message_count   INT DEFAULT 0,
    generation_count INT DEFAULT 0,
    input_tokens    BIGINT DEFAULT 0,
    output_tokens   BIGINT DEFAULT 0,
    cache_read_tokens BIGINT DEFAULT 0,
    cache_write_tokens BIGINT DEFAULT 0,
    cost_usd        NUMERIC(10,6),                 -- estimated cost

    -- Context
    cwd             TEXT,                          -- working directory
    git_branch      TEXT,
    git_repo        TEXT,                          -- 'akarelin/RAN'

    -- State
    status          TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'archived', 'merged'
    archived_at     TIMESTAMPTZ,
    merged_into_id  UUID REFERENCES sessions(id),  -- if merged, points to target

    -- Langfuse sync
    langfuse_trace_id TEXT,                        -- trace ID in Langfuse
    langfuse_synced_at TIMESTAMPTZ,

    -- Metadata
    tags            TEXT[] DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_source ON sessions(source);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_external ON sessions(external_id);
CREATE INDEX idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX idx_sessions_langfuse ON sessions(langfuse_trace_id);
CREATE INDEX idx_sessions_tags ON sessions USING GIN(tags);
CREATE INDEX idx_sessions_name_trgm ON sessions USING GIN(name gin_trgm_ops);

-- ============================================================================
-- SESSION CONTENT
-- ============================================================================

-- Individual messages within a session
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ordinal         INT NOT NULL,                  -- position in conversation

    role            TEXT NOT NULL,                  -- 'user', 'assistant', 'tool', 'system'
    content         TEXT,                          -- text content (truncated for large)
    content_hash    TEXT,                          -- hash of full content for dedup

    -- For assistant messages
    model           TEXT,
    input_tokens    INT,
    output_tokens   INT,
    thinking_tokens INT,
    stop_reason     TEXT,

    -- Tool calls
    tool_name       TEXT,                          -- if role='tool' or tool_use block
    tool_input      JSONB,
    tool_output     TEXT,

    timestamp       TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_messages_session ON messages(session_id, ordinal);
CREATE INDEX idx_messages_role ON messages(session_id, role);

-- Full JSONL content stored as-is (for replay / export)
CREATE TABLE session_content (
    session_id      UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    jsonl           TEXT NOT NULL,                  -- full JSONL content
    format          TEXT NOT NULL DEFAULT 'jsonl',  -- 'jsonl', 'json'
    size_bytes      BIGINT,
    line_count      INT,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- RELATIONSHIPS
-- ============================================================================

-- Session-to-session relationships
CREATE TABLE session_relations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    relation_type   TEXT NOT NULL,                  -- 'continuation', 'related', 'parent', 'child', 'merged_from'
    confidence      REAL,                          -- 0.0-1.0 for LLM-detected relations
    created_by      TEXT,                          -- 'manual', 'llm-auto', 'llm-correlate'
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(source_id, target_id, relation_type)
);

CREATE INDEX idx_relations_source ON session_relations(source_id);
CREATE INDEX idx_relations_target ON session_relations(target_id);
CREATE INDEX idx_relations_type ON session_relations(relation_type);

-- ============================================================================
-- TAGS & LABELS
-- ============================================================================

-- Canonical tag definitions (optional, for controlled vocabulary)
CREATE TABLE tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,           -- 'sprint-3', 'bugfix', 'exploration'
    color           TEXT,                          -- hex color for UI
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- LLM ANALYSIS RESULTS
-- ============================================================================

-- Store LLM-generated analysis (names, correlations, summaries)
CREATE TABLE llm_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES sessions(id) ON DELETE CASCADE,
    analysis_type   TEXT NOT NULL,                  -- 'name', 'summary', 'correlate', 'categorize'
    model           TEXT NOT NULL,                  -- 'claude-sonnet-4-6'
    prompt_hash     TEXT,                          -- hash of prompt for cache
    input_tokens    INT,
    output_tokens   INT,
    result          JSONB NOT NULL,                -- structured result
    applied         BOOLEAN DEFAULT FALSE,         -- was this applied to the session?
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_analyses_session ON llm_analyses(session_id);
CREATE INDEX idx_analyses_type ON llm_analyses(analysis_type);

-- ============================================================================
-- SYNC & AUDIT
-- ============================================================================

-- Track what's been synced to/from Langfuse
CREATE TABLE sync_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES sessions(id) ON DELETE CASCADE,
    direction       TEXT NOT NULL,                  -- 'deposit', 'withdraw'
    target          TEXT NOT NULL,                  -- 'langfuse', 'local'
    status          TEXT NOT NULL,                  -- 'success', 'failed', 'skipped'
    error           TEXT,
    langfuse_trace_id TEXT,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sync_session ON sync_log(session_id);

-- Audit trail for all session operations
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    session_id      UUID REFERENCES sessions(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,                  -- 'create', 'rename', 'archive', 'merge', 'delete', 'deposit', 'tag'
    details         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_session ON audit_log(session_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active sessions with project info
CREATE VIEW v_sessions AS
SELECT
    s.*,
    p.slug AS project_slug,
    p.name AS project_name,
    u.username,
    u.display_name AS user_display_name,
    COALESCE(s.input_tokens + s.output_tokens + s.cache_read_tokens + s.cache_write_tokens, 0) AS total_tokens
FROM sessions s
LEFT JOIN projects p ON s.project_id = p.id
LEFT JOIN users u ON s.user_id = u.id
WHERE s.status != 'archived';

-- Project summary
CREATE VIEW v_project_stats AS
SELECT
    p.id,
    p.slug,
    p.name,
    COUNT(s.id) AS session_count,
    SUM(s.input_tokens) AS total_input_tokens,
    SUM(s.output_tokens) AS total_output_tokens,
    SUM(s.cost_usd) AS total_cost,
    MIN(s.started_at) AS first_session,
    MAX(s.started_at) AS last_session,
    array_agg(DISTINCT s.model) FILTER (WHERE s.model IS NOT NULL) AS models_used,
    array_agg(DISTINCT s.source) AS sources
FROM projects p
LEFT JOIN sessions s ON s.project_id = p.id AND s.status != 'archived'
GROUP BY p.id, p.slug, p.name;

-- User activity summary
CREATE VIEW v_user_activity AS
SELECT
    u.id,
    u.username,
    COUNT(s.id) AS session_count,
    SUM(s.input_tokens) AS total_input_tokens,
    SUM(s.output_tokens) AS total_output_tokens,
    SUM(s.cost_usd) AS total_cost,
    MAX(s.started_at) AS last_session,
    COUNT(DISTINCT s.project_id) AS project_count,
    array_agg(DISTINCT s.source) AS sources
FROM users u
LEFT JOIN sessions s ON s.user_id = u.id AND s.status != 'archived'
GROUP BY u.id, u.username;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_updated
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER projects_updated
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- for fuzzy text search on session names
-- CREATE EXTENSION IF NOT EXISTS pgvector;   -- future: semantic search on session content

-- ============================================================================
-- SEED DATA
-- ============================================================================

INSERT INTO users (username, display_name, email) VALUES
    ('alex', 'Alex Karelin', 'alex@karel.in');
