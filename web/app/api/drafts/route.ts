import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

// Database path
const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status'); // pending, approved, rejected, sent
    const limit = parseInt(searchParams.get('limit') || '50');
    
    const db = new Database(DB_PATH, { readonly: true });
    
    let query = `
      SELECT 
        d.*,
        e.subject,
        e.from_email,
        e.from_name,
        e.priority_score,
        e.priority_category,
        e.received_at
      FROM draft_responses d
      JOIN emails e ON d.email_id = e.id
    `;
    
    const params: any[] = [];
    
    if (status && status !== 'all') {
      query += ` WHERE d.status = ?`;
      params.push(status);
    }
    
    query += ` ORDER BY d.created_at DESC LIMIT ?`;
    params.push(limit);
    
    const drafts = db.prepare(query).all(...params);
    
    // Get counts by status
    const countQuery = `
      SELECT 
        status,
        COUNT(*) as count
      FROM draft_responses
      GROUP BY status
    `;
    const counts = db.prepare(countQuery).all() as { status: string; count: number }[];
    
    const countMap: Record<string, number> = {
      pending: 0,
      approved: 0,
      rejected: 0,
      sent: 0,
    };
    
    counts.forEach(row => {
      countMap[row.status] = row.count;
    });
    
    db.close();
    
    return NextResponse.json({
      success: true,
      drafts,
      counts: countMap,
      total: drafts.length,
    });
    
  } catch (error: any) {
    console.error('Error fetching drafts:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
