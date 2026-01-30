import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

// GET single draft with history
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const db = new Database(DB_PATH, { readonly: true });
    
    // Get draft details
    const draft = db.prepare(`
      SELECT 
        d.*,
        e.subject,
        e.from_email,
        e.from_name,
        e.body,
        e.snippet,
        e.priority_score,
        e.priority_category,
        e.received_at
      FROM draft_responses d
      JOIN emails e ON d.email_id = e.id
      WHERE d.id = ?
    `).get(id);
    
    if (!draft) {
      return NextResponse.json(
        { success: false, error: 'Draft not found' },
        { status: 404 }
      );
    }
    
    // Get history
    const history = db.prepare(`
      SELECT * FROM draft_approval_history
      WHERE draft_id = ?
      ORDER BY performed_at DESC
    `).all(id);
    
    // Get versions
    let versions: any[] = [];
    try {
      versions = db.prepare(`
        SELECT * FROM draft_versions
        WHERE draft_id = ?
        ORDER BY version_number DESC
      `).all(id);
    } catch (e) {
      // versions table might not exist
    }
    
    db.close();
    
    return NextResponse.json({
      success: true,
      draft,
      history,
      versions,
    });
    
  } catch (error: any) {
    console.error('Error fetching draft:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// PATCH - Update draft (approve, reject, edit, rate)
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { action, ...data } = body;
    
    const db = new Database(DB_PATH);
    const now = new Date().toISOString();
    
    switch (action) {
      case 'approve': {
        db.prepare(`
          UPDATE draft_responses
          SET approved_at = ?, approved_by = ?, status = 'approved'
          WHERE id = ?
        `).run(now, data.by || 'user', id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes)
          VALUES (?, 'approved', ?, ?, ?)
        `).run(id, data.by || 'user', now, data.notes || null);
        break;
      }
      
      case 'reject': {
        db.prepare(`
          UPDATE draft_responses
          SET rejected_at = ?, rejected_by = ?, rejection_reason = ?, status = 'rejected'
          WHERE id = ?
        `).run(now, data.by || 'user', data.reason || null, id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes)
          VALUES (?, 'rejected', ?, ?, ?)
        `).run(id, data.by || 'user', now, data.reason || null);
        break;
      }
      
      case 'edit': {
        db.prepare(`
          UPDATE draft_responses
          SET edited_text = ?
          WHERE id = ?
        `).run(data.text, id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
          VALUES (?, 'edited', ?, ?, ?, ?)
        `).run(id, data.by || 'user', now, data.notes || null, JSON.stringify({ length: data.text?.length }));
        break;
      }
      
      case 'sent': {
        db.prepare(`
          UPDATE draft_responses
          SET sent_at = ?, sent_via = ?, status = 'sent'
          WHERE id = ?
        `).run(now, data.via || 'manual', id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
          VALUES (?, 'sent', ?, ?, ?, ?)
        `).run(id, data.by || 'user', now, data.notes || null, JSON.stringify({ via: data.via || 'manual' }));
        break;
      }
      
      case 'rate': {
        if (data.score < 1 || data.score > 5) {
          return NextResponse.json(
            { success: false, error: 'Score must be 1-5' },
            { status: 400 }
          );
        }
        
        db.prepare(`
          UPDATE draft_responses
          SET feedback_score = ?, feedback_notes = ?
          WHERE id = ?
        `).run(data.score, data.notes || null, id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
          VALUES (?, 'rated', ?, ?, ?, ?)
        `).run(id, data.by || 'user', now, data.notes || null, JSON.stringify({ score: data.score }));
        break;
      }
      
      case 'save_version': {
        // Save current draft as a version before regenerating
        const currentDraft = db.prepare(`SELECT draft_text, model_used, total_versions FROM draft_responses WHERE id = ?`).get(id) as any;
        
        if (currentDraft) {
          const newVersion = (currentDraft.total_versions || 1);
          
          db.prepare(`
            INSERT INTO draft_versions (draft_id, version_number, draft_text, model_used, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
          `).run(id, newVersion, currentDraft.draft_text, currentDraft.model_used, data.by || 'user', data.notes || null);
          
          db.prepare(`
            UPDATE draft_responses SET total_versions = total_versions + 1 WHERE id = ?
          `).run(id);
        }
        break;
      }
      
      case 'restore_version': {
        // Restore a previous version
        const version = db.prepare(`
          SELECT * FROM draft_versions WHERE draft_id = ? AND version_number = ?
        `).get(id, data.version) as any;
        
        if (!version) {
          db.close();
          return NextResponse.json(
            { success: false, error: `Version ${data.version} not found` },
            { status: 404 }
          );
        }
        
        db.prepare(`
          UPDATE draft_responses
          SET draft_text = ?, current_version = ?
          WHERE id = ?
        `).run(version.draft_text, data.version, id);
        
        db.prepare(`
          INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
          VALUES (?, 'restored', ?, ?, ?, ?)
        `).run(id, data.by || 'user', now, `Restored to version ${data.version}`, JSON.stringify({ version: data.version }));
        break;
      }
      
      default:
        db.close();
        return NextResponse.json(
          { success: false, error: `Unknown action: ${action}` },
          { status: 400 }
        );
    }
    
    db.close();
    
    return NextResponse.json({
      success: true,
      action,
      id,
    });
    
  } catch (error: any) {
    console.error('Error updating draft:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
