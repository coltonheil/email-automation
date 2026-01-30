import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const sort = searchParams.get('sort') || 'recent'; // recent, count, priority
    
    const db = new Database(DB_PATH, { readonly: true });
    
    let orderBy = 'last_email_at DESC';
    if (sort === 'count') orderBy = 'total_emails_received DESC';
    if (sort === 'priority') orderBy = 'avg_priority_score DESC';
    
    const senders = db.prepare(`
      SELECT 
        from_email as email,
        MAX(from_name) as name,
        COUNT(*) as total_emails_received,
        MAX(received_at) as last_email_at,
        ROUND(AVG(priority_score), 1) as avg_priority_score,
        SUM(CASE WHEN is_unread = 1 THEN 1 ELSE 0 END) as unread_count,
        SUM(CASE WHEN priority_category = 'urgent' THEN 1 ELSE 0 END) as urgent_count
      FROM emails
      WHERE from_email IS NOT NULL AND from_email != ''
      GROUP BY from_email
      ORDER BY ${orderBy}
      LIMIT ?
    `).all(limit);
    
    // Get draft stats for each sender
    const draftStats = db.prepare(`
      SELECT 
        e.from_email as email,
        COUNT(d.id) as total_drafts,
        SUM(CASE WHEN d.status = 'approved' THEN 1 ELSE 0 END) as approved_drafts,
        SUM(CASE WHEN d.status = 'rejected' THEN 1 ELSE 0 END) as rejected_drafts
      FROM emails e
      LEFT JOIN draft_responses d ON e.id = d.email_id
      GROUP BY e.from_email
    `).all() as { email: string; total_drafts: number; approved_drafts: number; rejected_drafts: number }[];
    
    const draftMap = new Map(draftStats.map(s => [s.email, s]));
    
    // Merge draft stats into senders
    const sendersWithDrafts = senders.map((sender: any) => ({
      ...sender,
      drafts: draftMap.get(sender.email) || { total_drafts: 0, approved_drafts: 0, rejected_drafts: 0 }
    }));
    
    db.close();
    
    return NextResponse.json({
      success: true,
      senders: sendersWithDrafts,
      total: senders.length,
    });
    
  } catch (error: any) {
    console.error('Error fetching senders:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
