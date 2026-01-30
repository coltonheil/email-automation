import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

// This endpoint is called by Clawdbot to update a draft after AI editing
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { instruction, newDraftText, model } = body;
    
    if (!newDraftText) {
      return NextResponse.json(
        { success: false, error: 'newDraftText is required' },
        { status: 400 }
      );
    }
    
    const db = new Database(DB_PATH);
    const now = new Date().toISOString();
    
    // Get current draft to save as version
    const currentDraft = db.prepare(`
      SELECT draft_text, model_used, total_versions 
      FROM draft_responses 
      WHERE id = ?
    `).get(id) as any;
    
    if (!currentDraft) {
      db.close();
      return NextResponse.json(
        { success: false, error: 'Draft not found' },
        { status: 404 }
      );
    }
    
    // Save current as version before updating
    const newVersionNum = (currentDraft.total_versions || 1);
    
    try {
      db.prepare(`
        INSERT INTO draft_versions (draft_id, version_number, draft_text, model_used, created_by, notes)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run(id, newVersionNum, currentDraft.draft_text, currentDraft.model_used, 'ai-edit', instruction || 'AI edit');
    } catch (e) {
      // versions table might not exist, continue anyway
    }
    
    // Update draft with new text
    db.prepare(`
      UPDATE draft_responses
      SET edited_text = ?, model_used = ?, total_versions = COALESCE(total_versions, 1) + 1
      WHERE id = ?
    `).run(newDraftText, model || 'claude-opus', id);
    
    // Log the edit action
    db.prepare(`
      INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
      VALUES (?, 'ai_edited', 'claude-opus', ?, ?, ?)
    `).run(id, now, instruction || 'AI edit', JSON.stringify({ 
      model: model || 'claude-opus',
      instruction: instruction,
      prev_length: currentDraft.draft_text.length,
      new_length: newDraftText.length
    }));
    
    db.close();
    
    return NextResponse.json({
      success: true,
      id,
      message: 'Draft updated via AI',
      versionSaved: newVersionNum
    });
    
  } catch (error: any) {
    console.error('Error in AI edit:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// GET the context needed for AI editing (original email + current draft)
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
    
    // Return context for AI editing
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
