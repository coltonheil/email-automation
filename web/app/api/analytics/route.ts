import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'database', 'emails.db');

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get('days') || '7');
    
    const db = new Database(DB_PATH, { readonly: true });
    
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString();
    
    // Email statistics
    const emailStats = db.prepare(`
      SELECT 
        COUNT(*) as total_emails,
        SUM(CASE WHEN is_unread = 1 THEN 1 ELSE 0 END) as unread_emails,
        SUM(CASE WHEN priority_category = 'urgent' THEN 1 ELSE 0 END) as urgent_emails,
        SUM(CASE WHEN priority_category = 'normal' THEN 1 ELSE 0 END) as normal_emails,
        SUM(CASE WHEN priority_category = 'low' THEN 1 ELSE 0 END) as low_emails,
        ROUND(AVG(priority_score), 1) as avg_priority
      FROM emails
      WHERE received_at >= ?
    `).get(cutoffStr) as any;
    
    // Draft statistics
    const draftStats = db.prepare(`
      SELECT 
        COUNT(*) as total_drafts,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_drafts,
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_drafts,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_drafts,
        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_drafts,
        ROUND(AVG(feedback_score), 1) as avg_rating
      FROM draft_responses
      WHERE created_at >= ?
    `).get(cutoffStr) as any;
    
    // API usage statistics
    let apiStats: any = {
      total_calls: 0,
      claude_calls: 0,
      composio_calls: 0,
      total_tokens: 0,
      total_cost: 0,
    };
    
    try {
      const apiResult = db.prepare(`
        SELECT 
          COUNT(*) as total_calls,
          SUM(CASE WHEN service = 'claude' THEN 1 ELSE 0 END) as claude_calls,
          SUM(CASE WHEN service = 'composio' THEN 1 ELSE 0 END) as composio_calls,
          COALESCE(SUM(tokens_used), 0) as total_tokens,
          COALESCE(SUM(cost_usd), 0) as total_cost
        FROM api_usage
        WHERE timestamp >= ?
      `).get(cutoffStr);
      if (apiResult) apiStats = apiResult;
    } catch (e) {
      // api_usage table might not exist
    }
    
    // Emails per day (for chart)
    const emailsPerDay = db.prepare(`
      SELECT 
        DATE(received_at) as date,
        COUNT(*) as count
      FROM emails
      WHERE received_at >= ?
      GROUP BY DATE(received_at)
      ORDER BY date
    `).all(cutoffStr);
    
    // Drafts per day (for chart)
    const draftsPerDay = db.prepare(`
      SELECT 
        DATE(created_at) as date,
        COUNT(*) as count
      FROM draft_responses
      WHERE created_at >= ?
      GROUP BY DATE(created_at)
      ORDER BY date
    `).all(cutoffStr);
    
    // Top senders
    const topSenders = db.prepare(`
      SELECT 
        from_email as email,
        MAX(from_name) as name,
        COUNT(*) as email_count,
        ROUND(AVG(priority_score), 1) as avg_priority
      FROM emails
      WHERE received_at >= ?
      GROUP BY from_email
      ORDER BY email_count DESC
      LIMIT 10
    `).all(cutoffStr);
    
    // Priority distribution
    const priorityDistribution = db.prepare(`
      SELECT 
        priority_category as category,
        COUNT(*) as count
      FROM emails
      WHERE received_at >= ?
      GROUP BY priority_category
    `).all(cutoffStr);
    
    db.close();
    
    // Calculate acceptance rate
    const acceptanceRate = draftStats.total_drafts > 0 
      ? ((draftStats.approved_drafts + draftStats.sent_drafts) / draftStats.total_drafts * 100).toFixed(1)
      : '0.0';
    
    return NextResponse.json({
      success: true,
      period: {
        days,
        from: cutoffStr,
        to: new Date().toISOString(),
      },
      emails: {
        ...emailStats,
        per_day: emailsPerDay,
      },
      drafts: {
        ...draftStats,
        acceptance_rate: parseFloat(acceptanceRate),
        per_day: draftsPerDay,
      },
      api: apiStats,
      top_senders: topSenders,
      priority_distribution: priorityDistribution,
    });
    
  } catch (error: any) {
    console.error('Error fetching analytics:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
