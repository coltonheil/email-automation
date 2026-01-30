-- Migration: Add Email Threading
-- Created: 2026-01-30
-- Purpose: Group emails into conversation threads

-- Email threads table
CREATE TABLE IF NOT EXISTS email_threads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id TEXT UNIQUE NOT NULL,  -- Gmail/Outlook thread ID
  subject TEXT,                     -- Thread subject (normalized)
  participants TEXT,                -- JSON array of email addresses
  email_count INTEGER DEFAULT 0,   -- Number of emails in thread
  last_email_at TEXT,              -- Most recent email timestamp
  first_email_at TEXT,             -- First email timestamp
  is_unread INTEGER DEFAULT 0,     -- Has unread emails
  max_priority INTEGER DEFAULT 0,  -- Highest priority in thread
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_threads_thread_id ON email_threads(thread_id);
CREATE INDEX IF NOT EXISTS idx_threads_last_email ON email_threads(last_email_at DESC);
CREATE INDEX IF NOT EXISTS idx_threads_unread ON email_threads(is_unread);
CREATE INDEX IF NOT EXISTS idx_threads_priority ON email_threads(max_priority DESC);

-- Add thread reference to emails table
ALTER TABLE emails ADD COLUMN thread_id TEXT;
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);

-- Thread participants junction table (for efficient querying)
CREATE TABLE IF NOT EXISTS thread_participants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id TEXT NOT NULL,
  email TEXT NOT NULL,
  name TEXT,
  role TEXT,  -- 'sender', 'recipient', 'cc'
  message_count INTEGER DEFAULT 1,
  first_seen TEXT,
  last_seen TEXT,
  UNIQUE(thread_id, email)
);

CREATE INDEX IF NOT EXISTS idx_thread_participants_thread ON thread_participants(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_participants_email ON thread_participants(email);
