-- app/data/schema.sql
-- SQLite schema for ALS assistant backend (production-ready).
-- Enable foreign keys.
PRAGMA foreign_keys = ON;

-- ---------- users ----------
CREATE TABLE IF NOT EXISTS users (
  id              TEXT PRIMARY KEY,
  email           TEXT UNIQUE,
  display_name    TEXT,
  created_at      DATETIME DEFAULT (datetime('now'))
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
  asked_qids        TEXT,                -- JSON array
  followup_ptr      INTEGER DEFAULT 0,
  lock_until_turn   INTEGER DEFAULT 0,
  turn_index        INTEGER DEFAULT 0,
  last_info_turn    INTEGER DEFAULT -999,
  pnm_scores        TEXT DEFAULT '[]',   -- JSON array of PNM scores
  evidence_count    TEXT DEFAULT '{}',   -- JSON object of evidence counts
  created_at        DATETIME DEFAULT (datetime('now')),
  updated_at        DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);

-- ---------- turns ----------
CREATE TABLE IF NOT EXISTS turns (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   TEXT NOT NULL,
  turn_index   INTEGER NOT NULL,      -- real turn id used by scorer
  role         TEXT NOT NULL,         -- 'user' | 'assistant' | ...
  text         TEXT,
  meta         TEXT,                  -- JSON object
  created_at   DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
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
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT NOT NULL,
  pnm         TEXT,
  term        TEXT,
  turn_id     INTEGER,                 -- optional FK to turns(id)
  snippet     TEXT,
  tag         TEXT,                    -- e.g., 'info', 'scoring'
  created_at  DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_sid ON evidence_log(session_id);
