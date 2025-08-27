-- Migration: Add conversations table for conversation history management
-- Date: 2025-08-26

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- 1. Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT DEFAULT NULL,  -- User editable title, NULL means auto-generate
    conversation_type TEXT DEFAULT 'general',  -- 'general' | 'dimension_specific'
    dimension_name TEXT,  -- For dimension-specific conversations
    status TEXT DEFAULT 'active',  -- 'active' | 'completed' | 'interrupted'
    session_id TEXT UNIQUE,  -- Links to sessions table
    started_at DATETIME DEFAULT (datetime('now')),
    completed_at DATETIME,
    last_activity DATETIME DEFAULT (datetime('now')),
    metadata TEXT DEFAULT '{}',  -- JSON for additional data
    summary TEXT,  -- Auto-generated summary when completed
    message_count INTEGER DEFAULT 0,
    info_card_count INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity DESC);

-- 2. Add conversation_id to turns table (with migration for existing data)
ALTER TABLE turns ADD COLUMN conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_turns_conversation_id ON turns(conversation_id);

-- 3. Enhance evidence_log for info cards storage
ALTER TABLE evidence_log ADD COLUMN conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE;
ALTER TABLE evidence_log ADD COLUMN card_type TEXT DEFAULT 'info';  -- 'info' | 'recommendation' | 'resource'
ALTER TABLE evidence_log ADD COLUMN card_data TEXT;  -- JSON storage for full card data
ALTER TABLE evidence_log ADD COLUMN display_order INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_evidence_conversation_id ON evidence_log(conversation_id);

-- 4. Add user preferences for conversation management
CREATE TABLE IF NOT EXISTS user_conversation_preferences (
    user_id TEXT PRIMARY KEY,
    auto_title_format TEXT DEFAULT 'Record %d',  -- Format for auto-generated titles
    max_active_conversations INTEGER DEFAULT 1,  -- How many active conversations allowed
    warn_on_interrupt BOOLEAN DEFAULT 1,  -- Show warning when interrupting conversation
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Conversation tags for better organization (future feature)
CREATE TABLE IF NOT EXISTS conversation_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    UNIQUE(conversation_id, tag)
);

-- 6. Add trigger to update last_activity
CREATE TRIGGER IF NOT EXISTS update_conversation_activity
AFTER INSERT ON turns
FOR EACH ROW
WHEN NEW.conversation_id IS NOT NULL
BEGIN
    UPDATE conversations 
    SET last_activity = datetime('now'),
        message_count = message_count + 1
    WHERE id = NEW.conversation_id;
END;

-- 7. Add trigger to update info_card_count
CREATE TRIGGER IF NOT EXISTS update_conversation_card_count
AFTER INSERT ON evidence_log
FOR EACH ROW
WHEN NEW.conversation_id IS NOT NULL
BEGIN
    UPDATE conversations 
    SET info_card_count = info_card_count + 1
    WHERE id = NEW.conversation_id;
END;