import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

// Clawdbot gateway for AI processing
const CLAWDBOT_URL = 'http://localhost:18789';
const CLAWDBOT_TOKEN = process.env.CLAWDBOT_TOKEN || 'nLQNEdPibR0VkQM05E8vy32RpdaQ0QfGOXCn2I/uq9Q=';

// POST - Process AI edit request
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { instruction } = body;
    
    if (!instruction) {
      return NextResponse.json(
        { success: false, error: 'instruction is required' },
        { status: 400 }
      );
    }
    
    const db = new Database(DB_PATH);
    
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
    
    // Build prompt for Claude
    const prompt = `You are helping edit an email draft response. 

ORIGINAL EMAIL (what the user is replying to):
From: ${draft.from_name} <${draft.from_email}>
Subject: ${draft.subject}
Body: ${(draft.body || draft.snippet || '').slice(0, 2000)}

CURRENT DRAFT RESPONSE:
${currentDraft}

USER'S EDIT INSTRUCTION:
${instruction}

Please provide ONLY the updated draft text. Do not include any explanation, just the new draft email body. Do not include subject line or signature - just the email body text.`;

    // Call Anthropic API directly (faster than going through Clawdbot gateway)
    const anthropicKey = process.env.ANTHROPIC_API_KEY;
    
    let newDraftText: string;
    
    if (anthropicKey) {
      // Direct API call
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': anthropicKey,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1024,
          messages: [{ role: 'user', content: prompt }],
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Anthropic API error: ${response.status}`);
      }
      
      const result = await response.json();
      newDraftText = result.content[0]?.text || '';
    } else {
      // Fallback: Call Clawdbot gateway
      const response = await fetch(`${CLAWDBOT_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${CLAWDBOT_TOKEN}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: prompt,
          model: 'sonnet',
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Clawdbot API error: ${response.status}`);
      }
      
      const result = await response.json();
      newDraftText = result.response || result.content || '';
    }
    
    if (!newDraftText) {
      db.close();
      return NextResponse.json(
        { success: false, error: 'AI returned empty response' },
        { status: 500 }
      );
    }
    
    // Clean up the response (remove any markdown formatting)
    newDraftText = newDraftText
      .replace(/^```[\s\S]*?\n/, '')
      .replace(/\n```$/, '')
      .trim();
    
    const now = new Date().toISOString();
    
    // Save current as version before updating
    const newVersionNum = (draft.total_versions || 1);
    try {
      db.prepare(`
        INSERT INTO draft_versions (draft_id, version_number, draft_text, model_used, created_by, notes)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run(id, newVersionNum, currentDraft, draft.model_used || 'unknown', 'ai-edit', instruction);
    } catch (e) {
      // versions table might not exist
    }
    
    // Update draft with new text
    db.prepare(`
      UPDATE draft_responses
      SET edited_text = ?, model_used = 'claude-sonnet', total_versions = COALESCE(total_versions, 1) + 1
      WHERE id = ?
    `).run(newDraftText, id);
    
    // Log the edit
    db.prepare(`
      INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
      VALUES (?, 'ai_edited', 'claude-sonnet', ?, ?, ?)
    `).run(id, now, instruction, JSON.stringify({ 
      instruction,
      prev_length: currentDraft.length,
      new_length: newDraftText.length
    }));
    
    db.close();
    
    return NextResponse.json({
      success: true,
      id,
      newDraftText,
      instruction,
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
