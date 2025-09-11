-- Document-based Conversation System Schema
-- Replaces complex multi-table structure with simple document storage

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ---------- users ----------
CREATE TABLE IF NOT EXISTS users (
  id              TEXT PRIMARY KEY,
  email           TEXT UNIQUE NOT NULL,
  password_hash   TEXT NOT NULL,
  display_name    TEXT NOT NULL,
  is_active       BOOLEAN DEFAULT 1,
  last_login      DATETIME,
  created_at      DATETIME DEFAULT (datetime('now')),
  updated_at      DATETIME DEFAULT (datetime('now'))
);

-- ---------- conversation_documents (NEW - main table) ----------
CREATE TABLE IF NOT EXISTS conversation_documents (
    id TEXT PRIMARY KEY,                    -- conversation_id
    user_id TEXT NOT NULL,
    title TEXT,
    type TEXT DEFAULT 'assessment',         -- 'assessment' | 'general_chat' | 'follow_up'
    dimension TEXT,                         -- PNM dimension if applicable
    status TEXT DEFAULT 'active',           -- 'active' | 'completed' | 'paused' | 'archived'
    
    -- Complete conversation document (JSON)
    document TEXT NOT NULL,                 -- Full ConversationDocument JSON
    
    -- Index fields extracted from JSON for query optimization
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    message_count INTEGER DEFAULT 0,
    last_message_at DATETIME,
    
    -- Assessment state fields for indexing
    current_pnm TEXT,
    current_term TEXT,
    fsm_state TEXT DEFAULT 'ROUTE',
    turn_index INTEGER DEFAULT 0,
    
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for conversation_documents
CREATE INDEX IF NOT EXISTS idx_conv_docs_user_status ON conversation_documents(user_id, status);
CREATE INDEX IF NOT EXISTS idx_conv_docs_type ON conversation_documents(type);
CREATE INDEX IF NOT EXISTS idx_conv_docs_dimension ON conversation_documents(dimension);
CREATE INDEX IF NOT EXISTS idx_conv_docs_updated ON conversation_documents(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_docs_user_updated ON conversation_documents(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_docs_fsm_state ON conversation_documents(fsm_state);

-- ---------- conversation_scores (index table for quick queries) ----------
CREATE TABLE IF NOT EXISTS conversation_scores (
    conversation_id TEXT,
    pnm TEXT,
    term TEXT,
    score REAL,
    status TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(conversation_id, pnm, term),
    FOREIGN KEY(conversation_id) REFERENCES conversation_documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conv_scores_conv_id ON conversation_scores(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_scores_pnm ON conversation_scores(pnm);

-- ---------- user_preferences (optional) ----------
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferences TEXT DEFAULT '{}',        -- JSON preferences
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------- Drop old complex tables ----------
-- These will be dropped after migration is complete
-- DROP TABLE IF EXISTS conversations;
-- DROP TABLE IF EXISTS turns; 
-- DROP TABLE IF EXISTS sessions;
-- DROP TABLE IF EXISTS evidence_log;
-- DROP TABLE IF EXISTS term_scores;
-- DROP TABLE IF EXISTS dimension_scores;

-- ---------- Migration helper views ----------
-- View to help with data migration from old structure
CREATE VIEW IF NOT EXISTS old_conversation_data AS
SELECT 
    c.id as conversation_id,
    c.user_id,
    c.title,
    c.conversation_type,
    c.dimension_name,
    c.status,
    c.session_id,
    c.started_at,
    c.completed_at,
    c.last_activity,
    c.message_count,
    s.current_pnm,
    s.current_term,
    s.fsm_state,
    s.turn_index
FROM conversations c
LEFT JOIN sessions s ON c.session_id = s.session_id;