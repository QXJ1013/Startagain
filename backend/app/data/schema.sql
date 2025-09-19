-- ALS Assistant System - Unified Complete Schema
-- Generated from current working database structure
-- 数据库统一完整Schema - 基于当前实际工作数据库结构生成

-- Users table - 用户表
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Sessions table - 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Conversation Documents - 对话文档表 (JSON存储)
CREATE TABLE IF NOT EXISTS conversation_documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'general_chat',
    dimension TEXT,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    messages TEXT NOT NULL DEFAULT '[]',
    assessment_state TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Conversation Scores - 对话评分表
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

-- Term Scores - 术语评分表
CREATE TABLE IF NOT EXISTS term_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pnm TEXT NOT NULL,
    term TEXT NOT NULL,
    score REAL NOT NULL,
    scoring_method TEXT,
    rationale TEXT,
    confidence REAL,
    quality_of_life_impact TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Dimension Scores - 维度评分表
CREATE TABLE IF NOT EXISTS dimension_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    avg_score REAL NOT NULL,
    assessment_count INTEGER DEFAULT 0,
    last_assessment DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Evidence Log - 证据日志表
CREATE TABLE IF NOT EXISTS evidence_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    conversation_id TEXT,
    pnm TEXT,
    term TEXT,
    evidence_type TEXT NOT NULL,
    evidence_content TEXT NOT NULL,
    confidence_score REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversation_documents(id) ON DELETE CASCADE
);

-- Conversations - 旧版对话表 (保留向后兼容)
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    type TEXT DEFAULT 'general',
    dimension TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Turns - 对话轮次表 (旧版，保留向后兼容)
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'text',
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- User Preferences - 用户偏好表
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    notification_settings TEXT DEFAULT '{}',
    ui_preferences TEXT DEFAULT '{}',
    assessment_preferences TEXT DEFAULT '{}',
    privacy_settings TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Conversation Preferences - 用户对话偏好表
CREATE TABLE IF NOT EXISTS user_conversation_preferences (
    user_id TEXT,
    conversation_id TEXT,
    preferences TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, conversation_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversation_documents(id) ON DELETE CASCADE
);

-- Conversation Tags - 对话标签表
CREATE TABLE IF NOT EXISTS conversation_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversation_documents(id) ON DELETE CASCADE
);

-- User Direct Routes - 用户直接路由表
CREATE TABLE IF NOT EXISTS user_direct_routes (
    user_id TEXT,
    dimension TEXT,
    route_data TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, dimension),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User PNM Status - 用户PNM状态表
CREATE TABLE IF NOT EXISTS user_pnm_status (
    user_id TEXT,
    pnm TEXT,
    status_data TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, pnm),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Profiles - 用户档案表
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    profile_data TEXT DEFAULT '{}',
    medical_history TEXT DEFAULT '{}',
    preferences TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Old Conversation Data - 旧对话数据表 (保留历史数据)
CREATE TABLE IF NOT EXISTS old_conversation_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    data_type TEXT,
    data_content TEXT,
    migrated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance - 性能索引
CREATE INDEX IF NOT EXISTS idx_conversation_documents_user_id ON conversation_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_documents_type ON conversation_documents(type);
CREATE INDEX IF NOT EXISTS idx_conversation_documents_dimension ON conversation_documents(dimension);
CREATE INDEX IF NOT EXISTS idx_conversation_documents_status ON conversation_documents(status);
CREATE INDEX IF NOT EXISTS idx_conversation_documents_created_at ON conversation_documents(created_at);

CREATE INDEX IF NOT EXISTS idx_conv_scores_conv_id ON conversation_scores(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_scores_pnm ON conversation_scores(pnm);
CREATE INDEX IF NOT EXISTS idx_conv_scores_updated_at ON conversation_scores(updated_at);

CREATE INDEX IF NOT EXISTS idx_term_scores_user_id ON term_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_term_scores_pnm ON term_scores(pnm);
CREATE INDEX IF NOT EXISTS idx_term_scores_term ON term_scores(term);
CREATE INDEX IF NOT EXISTS idx_term_scores_updated_at ON term_scores(updated_at);

CREATE INDEX IF NOT EXISTS idx_dimension_scores_user_id ON dimension_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_dimension_scores_dimension ON dimension_scores(dimension);

CREATE INDEX IF NOT EXISTS idx_evidence_log_user_id ON evidence_log(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_log_conversation_id ON evidence_log(conversation_id);
CREATE INDEX IF NOT EXISTS idx_evidence_log_pnm ON evidence_log(pnm);
CREATE INDEX IF NOT EXISTS idx_evidence_log_timestamp ON evidence_log(timestamp);

CREATE INDEX IF NOT EXISTS idx_turns_conversation_id ON turns(conversation_id);
CREATE INDEX IF NOT EXISTS idx_turns_created_at ON turns(created_at);

CREATE INDEX IF NOT EXISTS idx_conversation_tags_conversation_id ON conversation_tags(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_tags_tag ON conversation_tags(tag);

-- Triggers for Automatic Updates - 自动更新触发器
CREATE TRIGGER IF NOT EXISTS update_conversation_documents_timestamp
    AFTER UPDATE ON conversation_documents
    BEGIN
        UPDATE conversation_documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_user_preferences_timestamp
    AFTER UPDATE ON user_preferences
    BEGIN
        UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
    END;

CREATE TRIGGER IF NOT EXISTS update_user_profiles_timestamp
    AFTER UPDATE ON user_profiles
    BEGIN
        UPDATE user_profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
    END;