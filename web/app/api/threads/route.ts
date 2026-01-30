import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const unreadOnly = searchParams.get('unread') === 'true';
    
    const db = new Database(DB_PATH, { readonly: true });
    
    let query = `
      SELECT 
        t.*,
        (SELECT COUNT(*) FROM emails WHERE thread_id = t.thread_id) as actual_email_count
      FROM email_threads t
    `;
    
    if (unreadOnly) {
      query += ` WHERE t.is_unread = 1`;
    }
    
    query += ` ORDER BY t.last_message_at DESC LIMIT ?`;
    
    const threads = db.prepare(query).all(limit);
    
    db.close();
    
    return NextResponse.json({
      success: true,
      threads,
      total: threads.length,
    });
    
  } catch (error: any) {
    console.error('Error fetching threads:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
