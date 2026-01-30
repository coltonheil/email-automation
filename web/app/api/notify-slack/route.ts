import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * POST /api/notify-slack
 * 
 * Posts email draft notification to Slack #exec-approvals
 * 
 * Body: {
 *   draft_id: number,
 *   email_subject: string,
 *   from_email: string,
 *   from_name: string,
 *   priority_score: number,
 *   draft_text: string,
 *   relationship_type: string
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Support both custom messages and draft notifications
    let message: string;
    let channel: string;
    
    if (body.message) {
      // Custom message (e.g., AI edit request)
      message = body.message;
      channel = body.channel || 'exec-approvals';
    } else {
      // Legacy draft notification format
      const {
        draft_id,
        email_subject,
        from_email,
        from_name,
        priority_score,
        draft_text,
        relationship_type,
      } = body;
      
      message = formatSlackMessage({
        draft_id,
        email_subject,
        from_email,
        from_name,
        priority_score,
        draft_text,
        relationship_type,
      });
      channel = 'exec-approvals';
    }

    // Write to a file that Clawdbot can pick up
    // This is a simple IPC mechanism
    const fs = await import('fs').then(m => m.promises);
    const path = await import('path');
    
    const notifyDir = path.join(process.cwd(), '..', 'data');
    const notifyFile = path.join(notifyDir, 'slack_notify.json');
    
    // Ensure directory exists
    await fs.mkdir(notifyDir, { recursive: true });
    
    // Write notification request
    await fs.writeFile(notifyFile, JSON.stringify({
      channel,
      message,
      timestamp: new Date().toISOString()
    }, null, 2));
    
    return NextResponse.json({
      success: true,
      message: 'Notification queued for Slack',
      channel,
      file: notifyFile
    });
  } catch (error: any) {
    console.error('Error posting to Slack:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

function formatSlackMessage(draft: any): string {
  const {
    draft_id,
    email_subject,
    from_email,
    from_name,
    priority_score,
    draft_text,
    relationship_type,
  } = draft;

  const relationship = relationship_type?.replace(/_/g, ' ') || 'unknown';

  return `
🚨 *URGENT EMAIL - Auto-Draft Ready*

*From:* ${from_name} <${from_email}>
*Subject:* ${email_subject}
*Priority:* ${priority_score}/100
*Relationship:* ${relationship.charAt(0).toUpperCase() + relationship.slice(1)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ *SUGGESTED DRAFT RESPONSE:*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

${draft_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Draft ID: ${draft_id}

⚠️ *REMINDER:* This is a DRAFT only. You must manually copy and send it from your email client.

_This draft was generated with AI assistance based on your email history with this sender._
`.trim();
}
