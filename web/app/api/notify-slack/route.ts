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
    const {
      draft_id,
      email_subject,
      from_email,
      from_name,
      priority_score,
      draft_text,
      relationship_type,
    } = body;

    // Format Slack message
    const message = formatSlackMessage({
      draft_id,
      email_subject,
      from_email,
      from_name,
      priority_score,
      draft_text,
      relationship_type,
    });

    // Post to Slack via Clawdbot message tool
    // This will be called from the Clawdbot context
    const slackChannel = 'exec-approvals';
    
    // For now, return the formatted message
    // In production, this would use the Clawdbot message tool
    
    return NextResponse.json({
      success: true,
      message: 'Draft notification formatted (Slack integration pending)',
      slack_message: message,
      channel: slackChannel,
      draft_id,
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
