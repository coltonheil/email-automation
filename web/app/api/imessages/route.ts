import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

/**
 * iMessage API - READ ONLY, DRAFT ONLY
 * 
 * ⛔ SAFETY: This API has NO send capability.
 *    It only reads messages and manages drafts.
 *    All responses must be manually sent by the human.
 */

// GET - List iMessages and drafts
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const view = searchParams.get('view') || 'drafts'; // drafts, messages, or stats
    const status = searchParams.get('status') || 'pending';
    const limit = parseInt(searchParams.get('limit') || '50');
    
    const db = new Database(DB_PATH, { readonly: true });
    
    if (view === 'stats') {
      // Get counts
      const pendingDrafts = db.prepare(`
        SELECT COUNT(*) as count FROM imessage_drafts WHERE status = 'pending'
      `).get() as any;
      
      const messagesNeedingDrafts = db.prepare(`
        SELECT COUNT(*) as count FROM imessages WHERE has_draft = 0
      `).get() as any;
      
      const totalMessages = db.prepare(`
        SELECT COUNT(*) as count FROM imessages
      `).get() as any;
      
      db.close();
      
      return NextResponse.json({
        success: true,
        stats: {
          pendingDrafts: pendingDrafts?.count || 0,
          messagesNeedingDrafts: messagesNeedingDrafts?.count || 0,
          totalMessages: totalMessages?.count || 0
        },
        note: '⛔ READ ONLY - No send capability'
      });
    }
    
    if (view === 'messages') {
      // Get iMessages needing drafts
      const messages = db.prepare(`
        SELECT * FROM imessages 
        WHERE has_draft = 0
        ORDER BY received_at DESC
        LIMIT ?
      `).all(limit);
      
      db.close();
      
      return NextResponse.json({
        success: true,
        messages,
        note: '⛔ READ ONLY - No send capability'
      });
    }
    
    // Default: get drafts
    const drafts = db.prepare(`
      SELECT 
        d.*,
        m.sender,
        m.chat,
        m.text as original_text,
        m.received_at as message_received_at
      FROM imessage_drafts d
      JOIN imessages m ON d.imessage_id = m.id
      WHERE d.status = ?
      ORDER BY d.created_at DESC
      LIMIT ?
    `).all(status, limit);
    
    // Get counts by status
    const counts = {
      pending: (db.prepare(`SELECT COUNT(*) as c FROM imessage_drafts WHERE status = 'pending'`).get() as any)?.c || 0,
      approved: (db.prepare(`SELECT COUNT(*) as c FROM imessage_drafts WHERE status = 'approved'`).get() as any)?.c || 0,
      rejected: (db.prepare(`SELECT COUNT(*) as c FROM imessage_drafts WHERE status = 'rejected'`).get() as any)?.c || 0,
      sent: (db.prepare(`SELECT COUNT(*) as c FROM imessage_drafts WHERE status = 'sent'`).get() as any)?.c || 0,
    };
    
    db.close();
    
    return NextResponse.json({
      success: true,
      drafts,
      counts,
      note: '⛔ DRAFT ONLY - No send capability. Copy and send manually.'
    });
    
  } catch (error: any) {
    console.error('Error fetching iMessages:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// PATCH - Update draft status (approve, reject, mark sent)
export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, action, reason } = body;
    
    if (!id || !action) {
      return NextResponse.json(
        { success: false, error: 'id and action required' },
        { status: 400 }
      );
    }
    
    const db = new Database(DB_PATH);
    const now = new Date().toISOString();
    
    switch (action) {
      case 'approve':
        db.prepare(`
          UPDATE imessage_drafts 
          SET status = 'approved', approved_at = ?
          WHERE id = ?
        `).run(now, id);
        break;
        
      case 'reject':
        db.prepare(`
          UPDATE imessage_drafts 
          SET status = 'rejected', rejected_at = ?, rejection_reason = ?
          WHERE id = ?
        `).run(now, reason || null, id);
        break;
        
      case 'sent':
        // ⛔ NOTE: This only MARKS as sent (for tracking).
        // The actual sending is done MANUALLY by the human.
        db.prepare(`
          UPDATE imessage_drafts 
          SET status = 'sent', sent_at = ?
          WHERE id = ?
        `).run(now, id);
        break;
        
      case 'edit':
        if (!body.text) {
          db.close();
          return NextResponse.json(
            { success: false, error: 'text required for edit' },
            { status: 400 }
          );
        }
        db.prepare(`
          UPDATE imessage_drafts 
          SET draft_text = ?
          WHERE id = ?
        `).run(body.text, id);
        break;
        
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
      id,
      action,
      note: '⛔ Remember: Send manually from Messages.app'
    });
    
  } catch (error: any) {
    console.error('Error updating iMessage draft:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
