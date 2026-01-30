-- Migration: Add Draft Approval Workflow
-- Created: 2026-01-30
-- Purpose: Track what happens to drafts after generation

-- Add approval workflow columns to draft_responses
ALTER TABLE draft_responses ADD COLUMN approved_at TEXT;
ALTER TABLE draft_responses ADD COLUMN approved_by TEXT;
ALTER TABLE draft_responses ADD COLUMN rejected_at TEXT;
ALTER TABLE draft_responses ADD COLUMN rejected_by TEXT;
ALTER TABLE draft_responses ADD COLUMN rejection_reason TEXT;
ALTER TABLE draft_responses ADD COLUMN edited_text TEXT;  -- User's edited version
ALTER TABLE draft_responses ADD COLUMN sent_at TEXT;     -- When user actually sent
ALTER TABLE draft_responses ADD COLUMN sent_via TEXT;    -- How it was sent (manual, gmail_ui, etc.)
ALTER TABLE draft_responses ADD COLUMN feedback_score INTEGER;  -- 1-5 rating
ALTER TABLE draft_responses ADD COLUMN feedback_notes TEXT;     -- User feedback

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_drafts_approved ON draft_responses(approved_at);
CREATE INDEX IF NOT EXISTS idx_drafts_rejected ON draft_responses(rejected_at);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON draft_responses(status);
CREATE INDEX IF NOT EXISTS idx_drafts_sent ON draft_responses(sent_at);

-- Create approval history table for audit trail
CREATE TABLE IF NOT EXISTS draft_approval_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL,
  action TEXT NOT NULL,  -- 'approved', 'rejected', 'edited', 'sent', 'rated'
  performed_by TEXT,
  performed_at TEXT NOT NULL,
  notes TEXT,
  metadata TEXT,  -- JSON with additional context
  FOREIGN KEY (draft_id) REFERENCES draft_responses(id)
);

CREATE INDEX IF NOT EXISTS idx_approval_history_draft ON draft_approval_history(draft_id);
CREATE INDEX IF NOT EXISTS idx_approval_history_action ON draft_approval_history(action);
CREATE INDEX IF NOT EXISTS idx_approval_history_time ON draft_approval_history(performed_at);
