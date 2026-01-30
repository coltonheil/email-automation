-- Migration: Add Rate Limiting & API Usage Tracking
-- Created: 2026-01-30
-- Purpose: Track API usage to prevent hammering and manage costs

-- API usage tracking table
CREATE TABLE IF NOT EXISTS api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL,          -- 'composio' or 'claude'
  action TEXT NOT NULL,            -- 'fetch_emails', 'generate_draft', etc.
  timestamp TEXT NOT NULL,         -- ISO timestamp
  tokens_used INTEGER,             -- Tokens consumed (if available)
  cost_usd REAL,                   -- Estimated cost in USD
  success INTEGER DEFAULT 1,       -- 1 = success, 0 = failure
  metadata TEXT,                   -- JSON with additional context
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_usage_service ON api_usage(service);
CREATE INDEX IF NOT EXISTS idx_api_usage_action ON api_usage(service, action);
CREATE INDEX IF NOT EXISTS idx_api_usage_success ON api_usage(success);

-- Draft generation tracking (to prevent duplicates)
CREATE TABLE IF NOT EXISTS draft_generation_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email_id INTEGER NOT NULL,       -- Email that was drafted
  sender_email TEXT NOT NULL,      -- Sender email address
  generated_at TEXT NOT NULL,      -- When draft was generated
  draft_id INTEGER,                -- Reference to draft_responses.id
  FOREIGN KEY (email_id) REFERENCES emails(id),
  FOREIGN KEY (draft_id) REFERENCES draft_responses(id)
);

CREATE INDEX IF NOT EXISTS idx_draft_log_email ON draft_generation_log(email_id);
CREATE INDEX IF NOT EXISTS idx_draft_log_sender_time ON draft_generation_log(sender_email, generated_at);

-- Rate limit statistics (for monitoring)
CREATE TABLE IF NOT EXISTS rate_limit_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,              -- Date (YYYY-MM-DD)
  hour INTEGER,                    -- Hour of day (0-23)
  service TEXT NOT NULL,           -- 'composio' or 'claude'
  calls_made INTEGER DEFAULT 0,   -- Number of API calls
  calls_blocked INTEGER DEFAULT 0, -- Calls blocked by rate limiter
  tokens_used INTEGER DEFAULT 0,   -- Total tokens
  cost_usd REAL DEFAULT 0,         -- Total cost
  UNIQUE(date, hour, service)
);

CREATE INDEX IF NOT EXISTS idx_rate_stats_date ON rate_limit_stats(date);
CREATE INDEX IF NOT EXISTS idx_rate_stats_service ON rate_limit_stats(service);
