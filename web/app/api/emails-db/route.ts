import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import Database from 'better-sqlite3';

const execAsync = promisify(exec);

// Path to SQLite database
const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const filter = searchParams.get('filter') || 'all';
  const limit = parseInt(searchParams.get('limit') || '100');
  const sync = searchParams.get('sync') === 'true';

  try {
    // If sync requested, run background sync first
    if (sync) {
      // Trigger sync in background (don't wait for it)
      execAsync(
        `cd ${path.join(process.cwd(), '..')} && python3 scripts/sync_emails.py --mode incremental --limit 20`,
        { timeout: 30000 }
      ).catch(err => console.error('Background sync failed:', err));
    }

    // Read from database (instant)
    const db = new Database(DB_PATH, { readonly: true });
    
    let emails: any[] = [];
    
    if (filter === 'all') {
      emails = db.prepare(`
        SELECT * FROM emails
        ORDER BY received_at DESC
        LIMIT ?
      `).all(limit);
    } else if (filter === 'unread') {
      emails = db.prepare(`
        SELECT * FROM emails
        WHERE is_unread = 1
        ORDER BY priority_score DESC, received_at DESC
        LIMIT ?
      `).all(limit);
    } else if (filter === 'urgent') {
      emails = db.prepare(`
        SELECT * FROM emails
        WHERE priority_category = 'urgent'
        ORDER BY received_at DESC
        LIMIT ?
      `).all(limit);
    } else if (filter === 'normal') {
      emails = db.prepare(`
        SELECT * FROM emails
        WHERE priority_category = 'normal'
        ORDER BY received_at DESC
        LIMIT ?
      `).all(limit);
    } else if (filter === 'low') {
      emails = db.prepare(`
        SELECT * FROM emails
        WHERE priority_category = 'low'
        ORDER BY received_at DESC
        LIMIT ?
      `).all(limit);
    }
    
    // Parse JSON fields
    emails = emails.map(email => ({
      ...email,
      labels: email.labels ? JSON.parse(email.labels) : [],
      raw_data: email.raw_data ? JSON.parse(email.raw_data) : {},
      is_unread: Boolean(email.is_unread),
      is_important: Boolean(email.is_important),
      has_attachments: Boolean(email.has_attachments),
    }));
    
    db.close();

    return NextResponse.json({
      success: true,
      total_count: emails.length,
      emails,
      from_cache: !sync,
      fetched_at: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('Error reading from database:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error.message || 'Failed to read emails from database',
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, emailId } = body;

    const db = new Database(DB_PATH);

    if (action === 'mark_read') {
      db.prepare(`
        UPDATE emails
        SET is_unread = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `).run(emailId);
    } else if (action === 'mark_unread') {
      db.prepare(`
        UPDATE emails
        SET is_unread = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `).run(emailId);
    }

    db.close();

    return NextResponse.json({
      success: true,
      action,
      emailId,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
