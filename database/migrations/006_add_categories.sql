-- Migration: Add Smart Categories
-- Created: 2026-01-30
-- Purpose: Auto-categorize emails for better organization

-- Add category column to emails
ALTER TABLE emails ADD COLUMN category TEXT;

-- Create indexes for category queries
CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_emails_category_unread ON emails(category, is_unread);

-- Category stats table (for analytics)
CREATE TABLE IF NOT EXISTS category_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  category TEXT NOT NULL,
  email_count INTEGER DEFAULT 0,
  draft_count INTEGER DEFAULT 0,
  avg_priority REAL DEFAULT 0,
  UNIQUE(date, category)
);

CREATE INDEX IF NOT EXISTS idx_category_stats_date ON category_stats(date);
