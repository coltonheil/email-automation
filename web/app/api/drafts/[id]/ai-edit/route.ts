import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

// Ensure queue table exists
function ensureQueueTable(db: any) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS ai_edit_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      draft_id INTEGER NOT NULL,
      instruction TEXT NOT NULL,
      current_draft TEXT NOT NULL,
      original_email_json TEXT,
      status TEXT DEFAULT 'pending',
      result_text TEXT,
      error_message TEXT,
      created_at TEXT NOT NULL,
      processed_at TEXT,
      FOREIGN KEY (draft_id) REFERENCES draft_responses(id)
    )
  `);
}

// POST - Queue AI edit request for Clawdbot processing
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { instruction, poll_queue_id } = body;
    
    const db = new Database(DB_PATH);
    ensureQueueTable(db);
    
    // If polling for queue result
    if (poll_queue_id) {
      const queueItem = db.prepare(`
        SELECT * FROM ai_edit_queue WHERE id = ?
      `).get(poll_queue_id) as any;
      
      if (!queueItem) {
        db.close();
        return NextResponse.json({ success: false, error: 'Queue item not found' }, { status: 404 });
      }
      
      if (queueItem.status === 'completed') {
        db.close();
        return NextResponse.json({
          success: true,
          completed: true,
          newDraftText: queueItem.result_text,
          id: queueItem.draft_id
        });
      } else if (queueItem.status === 'failed') {
        db.close();
        return NextResponse.json({
          success: false,
          completed: true,
          error: queueItem.error_message || 'Processing failed'
        });
      } else {
        db.close();
        return NextResponse.json({
          success: true,
          completed: false,
          status: queueItem.status,
          message: 'Still processing...'
        });
      }
    }
    
    // New edit request
    if (!instruction) {
      db.close();
      return NextResponse.json(
        { success: false, error: 'instruction is required' },
        { status: 400 }
      );
    }
    
    // Get current draft and original email
    const draft = db.prepare(`
      SELECT 
        d.id,
        d.draft_text,
        d.edited_text,
        d.model_used,
        d.total_versions,
        e.subject,
        e.from_email,
        e.from_name,
        e.body,
        e.snippet
      FROM draft_responses d
      JOIN emails e ON d.email_id = e.id
      WHERE d.id = ?
    `).get(id) as any;
    
    if (!draft) {
      db.close();
      return NextResponse.json(
        { success: false, error: 'Draft not found' },
        { status: 404 }
      );
    }
    
    const currentDraft = draft.edited_text || draft.draft_text;
    const now = new Date().toISOString();
    
    const originalEmailJson = JSON.stringify({
      from_name: draft.from_name,
      from_email: draft.from_email,
      subject: draft.subject,
      body: (draft.body || draft.snippet || '').slice(0, 2000)
    });
    
    // Queue the edit request
    const result = db.prepare(`
      INSERT INTO ai_edit_queue (draft_id, instruction, current_draft, original_email_json, status, created_at)
      VALUES (?, ?, ?, ?, 'pending', ?)
    `).run(id, instruction, currentDraft, originalEmailJson, now);
    
    const queueId = result.lastInsertRowid;
    
    // Notify Clawdbot via Slack
    try {
      const notifyUrl = `${request.nextUrl.origin}/api/notify-slack`;
      await fetch(notifyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: 'repo-email-automation',
          message: `🤖 *AI Edit Request Queued*\n\n*Queue ID:* ${queueId}\n*Draft ID:* ${id}\n*Instruction:* ${instruction.slice(0, 100)}${instruction.length > 100 ? '...' : ''}\n\n_Clawdbot: Please process this AI edit request._`
        })
      });
    } catch (e) {
      // Notification optional - don't fail the request
      console.error('Failed to send Slack notification:', e);
    }
    
    db.close();
    
    return NextResponse.json({
      success: true,
      queued: true,
      queue_id: Number(queueId),
      draft_id: id,
      message: 'Edit request queued. Clawdbot is processing...'
    });
    
  } catch (error: any) {
    console.error('Error in AI edit:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// GET the context needed for AI editing
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const db = new Database(DB_PATH, { readonly: true });
    
    const draft = db.prepare(`
      SELECT 
        d.id,
        d.draft_text,
        d.edited_text,
        d.model_used,
        e.subject,
        e.from_email,
        e.from_name,
        e.body,
        e.snippet
      FROM draft_responses d
      JOIN emails e ON d.email_id = e.id
      WHERE d.id = ?
    `).get(id) as any;
    
    db.close();
    
    if (!draft) {
      return NextResponse.json(
        { success: false, error: 'Draft not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({
      success: true,
      context: {
        draftId: draft.id,
        currentDraft: draft.edited_text || draft.draft_text,
        originalEmail: {
          subject: draft.subject,
          from: `${draft.from_name} <${draft.from_email}>`,
          body: draft.body,
          snippet: draft.snippet
        }
      }
    });
    
  } catch (error: any) {
    console.error('Error getting AI edit context:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
