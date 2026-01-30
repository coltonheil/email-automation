import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const db = new Database(DB_PATH, { readonly: true });
    
    // Get thread info
    const thread = db.prepare(`
      SELECT * FROM email_threads WHERE thread_id = ?
    `).get(id);
    
    if (!thread) {
      db.close();
      return NextResponse.json(
        { success: false, error: 'Thread not found' },
        { status: 404 }
      );
    }
    
    // Get all emails in thread
    const emails = db.prepare(`
      SELECT * FROM emails
      WHERE thread_id = ?
      ORDER BY received_at ASC
    `).all(id);
    
    // Get participants
    const participants = db.prepare(`
      SELECT * FROM thread_participants
      WHERE thread_id = ?
      ORDER BY message_count DESC
    `).all(id);
    
    db.close();
    
    return NextResponse.json({
      success: true,
      thread,
      emails,
      participants,
    });
    
  } catch (error: any) {
    console.error('Error fetching thread:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
