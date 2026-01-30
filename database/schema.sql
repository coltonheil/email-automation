-- Email Automation Database Schema
-- SQLite database for persistent email storage

-- Main emails table
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    account_id TEXT NOT NULL,
    message_id TEXT,
    thread_id TEXT,
    subject TEXT,
    from_email TEXT NOT NULL,
    from_name TEXT,
    to_email TEXT,
    cc TEXT,
    bcc TEXT,
    body TEXT,
    snippet TEXT,
    labels TEXT, -- JSON array
    is_unread BOOLEAN DEFAULT 1,
    is_important BOOLEAN DEFAULT 0,
    has_attachments BOOLEAN DEFAULT 0,
    received_at TIMESTAMP NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority_score INTEGER,
    priority_category TEXT,
    raw_data TEXT, -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sender profiles (for context building)
CREATE TABLE IF NOT EXISTS sender_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_address TEXT UNIQUE NOT NULL,
    name TEXT,
    total_emails_received INTEGER DEFAULT 0,
    last_email_at TIMESTAMP,
    avg_priority_score REAL,
    common_topics TEXT, -- JSON array
    relationship_type TEXT, -- 'business', 'personal', 'vendor', 'automated'
    response_pattern TEXT, -- 'always_respond', 'sometimes_respond', 'rarely_respond'
    typical_response_time_hours INTEGER,
    writing_style_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Draft responses
CREATE TABLE IF NOT EXISTS draft_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL,
    draft_text TEXT NOT NULL,
    model_used TEXT, -- e.g., 'claude-sonnet-4'
    generation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'edited', 'sent', 'dismissed'
    slack_message_ts TEXT, -- Slack message timestamp for updates
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id)
);

-- Sync log (track what we've synced)
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    sync_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_completed_at TIMESTAMP,
    emails_fetched INTEGER DEFAULT 0,
    new_emails INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running', -- 'running', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email threads (for conversation context)
CREATE TABLE IF NOT EXISTS email_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT UNIQUE NOT NULL,
    subject TEXT,
    participants TEXT, -- JSON array of email addresses
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_emails_unread ON emails(is_unread);
CREATE INDEX IF NOT EXISTS idx_emails_priority ON emails(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_emails_received ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_from ON emails(from_email);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_sender_email ON sender_profiles(email_address);
CREATE INDEX IF NOT EXISTS idx_drafts_email ON draft_responses(email_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON draft_responses(status);
CREATE INDEX IF NOT EXISTS idx_sync_account ON sync_log(account_id);
CREATE INDEX IF NOT EXISTS idx_threads_id ON email_threads(thread_id);

-- Views for common queries
CREATE VIEW IF NOT EXISTS unread_urgent_emails AS
SELECT 
    e.*,
    sp.name as sender_name,
    sp.relationship_type,
    sp.avg_priority_score as sender_avg_priority,
    dr.id as draft_id,
    dr.status as draft_status
FROM emails e
LEFT JOIN sender_profiles sp ON e.from_email = sp.email_address
LEFT JOIN draft_responses dr ON e.id = dr.email_id
WHERE e.is_unread = 1 
  AND e.priority_score >= 80
ORDER BY e.priority_score DESC, e.received_at DESC;

CREATE VIEW IF NOT EXISTS recent_emails AS
SELECT 
    e.*,
    sp.name as sender_name,
    sp.relationship_type
FROM emails e
LEFT JOIN sender_profiles sp ON e.from_email = sp.email_address
ORDER BY e.received_at DESC
LIMIT 100;
