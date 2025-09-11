-- app/data/schema.sql
-- SQLite schema for ALS assistant backend (production-ready).
-- Enable foreign keys.
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

-- ---------- sessions ----------
-- Note: session_id is unique and used as business key (not the INTEGER rowid).
CREATE TABLE IF NOT EXISTS sessions (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id        TEXT UNIQUE NOT NULL,
  user_id           TEXT,
  status            TEXT DEFAULT 'active',
  fsm_state         TEXT DEFAULT 'ROUTE',
  current_pnm       TEXT,
  current_term      TEXT,
  current_qid       TEXT,                -- NEW: stick to a single questionnaire across followups
  asked_qids        TEXT DEFAULT '[]',   -- JSON array
  followup_ptr      INTEGER DEFAULT 0,
  lock_until_turn   INTEGER DEFAULT 0,
  turn_index        INTEGER DEFAULT 0,
  last_info_turn    INTEGER DEFAULT -999,
  pnm_scores        TEXT DEFAULT '[]',   -- JSON array of PNM scores
  evidence_count    TEXT DEFAULT '{}',   -- JSON object of evidence counts
  keyword_pool      TEXT DEFAULT '[]',   -- JSON array of routing keywords
  ai_confidence     REAL DEFAULT 0.0,    -- AI routing confidence score
  routing_method    TEXT DEFAULT 'exact', -- Routing method used
  last_policy_decision TEXT DEFAULT 'structured', -- Policy decision type
  last_dialogue_prompt TEXT,              -- Last dialogue prompt
  created_at        DATETIME DEFAULT (datetime('now')),
  updated_at        DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);

-- ---------- turns ----------
CREATE TABLE IF NOT EXISTS turns (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL,
  conversation_id TEXT,                   -- Link to conversations table
  turn_index      INTEGER NOT NULL,       -- real turn id used by scorer
  role            TEXT NOT NULL,          -- 'user' | 'assistant' | ...
  text            TEXT,
  meta            TEXT,                   -- JSON object
  created_at      DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_conversation_id ON turns(conversation_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_turns_sid_idx ON turns(session_id, turn_index);

-- ---------- term_scores ----------
CREATE TABLE IF NOT EXISTS term_scores (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id         TEXT NOT NULL,
  pnm                TEXT NOT NULL,
  term               TEXT NOT NULL,
  score_0_7          REAL NOT NULL,
  rationale          TEXT,
  evidence_turn_ids  TEXT,                -- JSON array of real turn_index
  status             TEXT,                -- 'complete' | 'pending'
  method_version     TEXT,
  updated_at         DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Upsert key
CREATE UNIQUE INDEX IF NOT EXISTS idx_term_scores_sid_dim_term
  ON term_scores(session_id, pnm, term);

-- ---------- dimension_scores ----------
CREATE TABLE IF NOT EXISTS dimension_scores (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL,
  pnm             TEXT NOT NULL,
  score_0_7       REAL NOT NULL,
  coverage_ratio  REAL NOT NULL,
  stage           TEXT,
  method_version  TEXT,
  updated_at      DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_scores_sid_pnm
  ON dimension_scores(session_id, pnm);

-- ---------- evidence_log (optional trace) ----------
CREATE TABLE IF NOT EXISTS evidence_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL,
  conversation_id TEXT,                    -- Link to conversations
  pnm             TEXT,
  term            TEXT,
  turn_id         INTEGER,                 -- optional FK to turns(id)
  snippet         TEXT,
  tag             TEXT,                    -- e.g., 'info', 'scoring', 'info_card'
  card_type       TEXT,                    -- Type of info card
  card_data       TEXT,                    -- JSON data for info cards
  display_order   INTEGER DEFAULT 0,       -- Display order for cards
  created_at      DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_sid ON evidence_log(session_id);
CREATE INDEX IF NOT EXISTS idx_evidence_conversation_id ON evidence_log(conversation_id);

-- ---------- conversations ----------
-- Table for managing conversation history and state
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT DEFAULT NULL,
    conversation_type TEXT DEFAULT 'general',
    dimension_name TEXT,
    status TEXT DEFAULT 'active',
    session_id TEXT UNIQUE,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    summary TEXT,
    message_count INTEGER DEFAULT 0,
    info_card_count INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity DESC);

-- ---------- user conversation preferences ----------
CREATE TABLE IF NOT EXISTS user_conversation_preferences (
    user_id TEXT PRIMARY KEY,
    auto_title_format TEXT DEFAULT 'Record %d',
    max_active_conversations INTEGER DEFAULT 1,
    warn_on_interrupt BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------- conversation tags ----------
CREATE TABLE IF NOT EXISTS conversation_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    UNIQUE(conversation_id, tag)
);
