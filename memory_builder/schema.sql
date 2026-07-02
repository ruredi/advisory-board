PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    source_title TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'unknown',
    source_date TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    speaker TEXT,
    source_nature TEXT NOT NULL DEFAULT 'uncertain',
    raw_path TEXT,
    error_message TEXT,
    channel_url TEXT,
    normalized_title TEXT,
    UNIQUE(persona_id, source_url)
);

CREATE INDEX IF NOT EXISTS idx_sources_channel_url ON sources(persona_id, channel_url);
CREATE INDEX IF NOT EXISTS idx_sources_normalized_title ON sources(persona_id, normalized_title);
CREATE INDEX IF NOT EXISTS idx_sources_source_date ON sources(persona_id, source_date);

CREATE INDEX IF NOT EXISTS idx_sources_persona_status ON sources(persona_id, status);
CREATE INDEX IF NOT EXISTS idx_sources_content_hash ON sources(content_hash);

CREATE TABLE IF NOT EXISTS knowledge_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    visual_description TEXT NOT NULL DEFAULT '',
    topics TEXT NOT NULL DEFAULT '[]',
    frameworks TEXT NOT NULL DEFAULT '[]',
    processes TEXT NOT NULL DEFAULT '[]',
    steps TEXT NOT NULL DEFAULT '[]',
    concepts TEXT NOT NULL DEFAULT '[]',
    advice_contexts TEXT NOT NULL DEFAULT '[]',
    examples TEXT NOT NULL DEFAULT '[]',
    quotes TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT 'medium',
    retrieval_priority INTEGER NOT NULL DEFAULT 50,
    is_new_information INTEGER NOT NULL DEFAULT 1,
    duplicate_of INTEGER REFERENCES knowledge_units(id),
    speaker TEXT,
    source_nature TEXT NOT NULL DEFAULT 'uncertain',
    evidence_type TEXT NOT NULL DEFAULT 'source_supported',
    content_fingerprint TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_persona ON knowledge_units(persona_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_units(source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_content_type ON knowledge_units(content_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_fingerprint ON knowledge_units(content_fingerprint);

CREATE TABLE IF NOT EXISTS embeddings (
    knowledge_unit_id INTEGER PRIMARY KEY REFERENCES knowledge_units(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    embedding BLOB NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    sources_discovered INTEGER NOT NULL DEFAULT 0,
    sources_processed INTEGER NOT NULL DEFAULT 0,
    units_created INTEGER NOT NULL DEFAULT 0,
    units_skipped_duplicate INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    run_id INTEGER,
    source_id INTEGER,
    stage TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_run ON pipeline_events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_persona_created ON pipeline_events(persona_id, created_at);

CREATE TABLE IF NOT EXISTS api_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL,
    run_id INTEGER,
    source_id INTEGER,
    provider TEXT NOT NULL,
    operation TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    api_credits REAL NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    is_estimated INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_api_usage_persona_created ON api_usage_logs(persona_id, created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_run ON api_usage_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage_logs(persona_id, provider);
