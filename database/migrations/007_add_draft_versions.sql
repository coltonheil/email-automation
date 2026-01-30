-- Migration: Add Draft Version History
-- Created: 2026-01-30
-- Purpose: Track multiple versions of drafts (regenerations, edits)

CREATE TABLE IF NOT EXISTS draft_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL,
  version_number INTEGER NOT NULL,
  draft_text TEXT NOT NULL,
  model_used TEXT,
  created_by TEXT DEFAULT 'system',  -- 'system' for AI, 'user' for manual edits
  created_at TEXT DEFAULT (datetime('now')),
  notes TEXT,
  FOREIGN KEY (draft_id) REFERENCES draft_responses(id)
);

CREATE INDEX IF NOT EXISTS idx_draft_versions_draft ON draft_versions(draft_id);
CREATE INDEX IF NOT EXISTS idx_draft_versions_version ON draft_versions(draft_id, version_number);

-- Add version tracking to draft_responses
ALTER TABLE draft_responses ADD COLUMN current_version INTEGER DEFAULT 1;
ALTER TABLE draft_responses ADD COLUMN total_versions INTEGER DEFAULT 1;
