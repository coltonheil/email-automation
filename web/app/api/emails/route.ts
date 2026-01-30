import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const mode = searchParams.get('mode') || 'unread';
  const limit = searchParams.get('limit') || '20'; // Reduced from 100 to 20
  const hours = searchParams.get('hours') || '24';

  try {
    // Build command
    let command = `cd ${path.join(process.cwd(), '..')} && export COMPOSIO_API_KEY=$(grep COMPOSIO_API_KEY ~/clawd/.env | cut -d= -f2) && python3 scripts/fetch_all_emails.py --mode ${mode} --limit ${limit} --json`;
    
    if (mode === 'recent') {
      command += ` --hours ${hours}`;
    }

    // Execute Python script with 30-second timeout
    const { stdout, stderr } = await execAsync(command, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
      timeout: 30000, // 30 second timeout
    });

    if (stderr && !stderr.includes('Fetching') && stderr.trim()) {
      console.error('Script stderr:', stderr);
    }

    // Parse JSON output
    const data = JSON.parse(stdout);

    return NextResponse.json({
      success: true,
      total_count: data.total_count || 0,
      emails: data.emails || [],
      fetched_at: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('Error fetching emails:', error);
    
    // Check if it's a timeout error
    if (error.killed && error.signal === 'SIGTERM') {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Request timed out after 30 seconds. Try reducing the limit.',
          timeout: true,
        },
        { status: 504 }
      );
    }
    
    return NextResponse.json(
      { 
        success: false, 
        error: error.message || 'Failed to fetch emails',
        details: error.stderr || error.stdout,
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  // Handle email actions (mark read, archive, etc.)
  try {
    const body = await request.json();
    const { action, emailId } = body;

    // TODO: Implement email actions via Composio API
    // For now, return success
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
