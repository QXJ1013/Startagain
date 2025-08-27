-- Authentication schema updates
-- Run this to add authentication support

-- Update users table with password
ALTER TABLE users ADD COLUMN password_hash TEXT;

-- Ensure email is unique and not null for auth
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add authentication tracking fields
ALTER TABLE users ADD COLUMN last_login DATETIME;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1;

-- Sessions must have user_id (no more anonymous sessions)
-- We'll enforce this in application logic rather than DB constraint
-- to allow migration period

-- Optional: Add auth tokens table for refresh tokens later
CREATE TABLE IF NOT EXISTS auth_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  token_type TEXT DEFAULT 'refresh',
  expires_at DATETIME NOT NULL,
  created_at DATETIME DEFAULT (datetime('now')),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_user ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_hash ON auth_tokens(token_hash);