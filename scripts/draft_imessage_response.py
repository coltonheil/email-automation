#!/usr/bin/env python3
"""
Draft iMessage Response - DRAFT ONLY, NO SEND

⛔ SAFETY: This script ONLY creates drafts.
   It has NO send capability whatsoever.
   All drafts go to Slack for human review and manual sending.

Usage:
    python3 draft_imessage_response.py --message-id <id>
    python3 draft_imessage_response.py --all-unread
"""

import sqlite3
import os
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "emails.db"  # Reuse the same DB

def ensure_imessage_tables(conn):
    """Create iMessage tables if they don't exist."""
    
    # Table for storing fetched iMessages
    conn.execute('''
        CREATE TABLE IF NOT EXISTS imessages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_guid TEXT UNIQUE,
            sender TEXT NOT NULL,
            chat TEXT,
            text TEXT NOT NULL,
            received_at TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            priority_score INTEGER DEFAULT 50,
            has_draft INTEGER DEFAULT 0
        )
    ''')
    
    # Table for iMessage draft responses
    conn.execute('''
        CREATE TABLE IF NOT EXISTS imessage_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imessage_id INTEGER NOT NULL,
            draft_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            approved_at TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            sent_at TEXT,
            model_used TEXT DEFAULT 'claude-opus',
            FOREIGN KEY (imessage_id) REFERENCES imessages(id)
        )
    ''')
    
    conn.commit()

def store_imessage(conn, msg):
    """Store an iMessage in the database."""
    try:
        conn.execute('''
            INSERT OR IGNORE INTO imessages (message_guid, sender, chat, text, received_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (msg['guid'], msg['sender'], msg.get('chat'), msg['text'], msg.get('timestamp')))
        conn.commit()
        
        # Get the ID (either new or existing)
        cursor = conn.execute('SELECT id FROM imessages WHERE message_guid = ?', (msg['guid'],))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Error storing message: {e}", file=sys.stderr)
        return None

def create_draft(conn, imessage_id, draft_text, model="clawdbot"):
    """
    Create a draft response for an iMessage.
    
    ⛔ THIS ONLY CREATES A DRAFT - NO SENDING.
    """
    now = datetime.now().isoformat()
    
    cursor = conn.execute('''
        INSERT INTO imessage_drafts (imessage_id, draft_text, status, created_at, model_used)
        VALUES (?, ?, 'pending', ?, ?)
    ''', (imessage_id, draft_text, now, model))
    
    draft_id = cursor.lastrowid
    
    # Mark the message as having a draft
    conn.execute('UPDATE imessages SET has_draft = 1 WHERE id = ?', (imessage_id,))
    conn.commit()
    
    return draft_id

def get_pending_imessages(conn, limit=10):
    """Get iMessages that need draft responses."""
    cursor = conn.execute('''
        SELECT * FROM imessages 
        WHERE has_draft = 0
        ORDER BY received_at DESC
        LIMIT ?
    ''', (limit,))
    
    return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

def get_imessage_drafts(conn, status='pending', limit=20):
    """Get iMessage drafts by status."""
    cursor = conn.execute('''
        SELECT d.*, m.sender, m.chat, m.text as original_text, m.received_at
        FROM imessage_drafts d
        JOIN imessages m ON d.imessage_id = m.id
        WHERE d.status = ?
        ORDER BY d.created_at DESC
        LIMIT ?
    ''', (status, limit))
    
    return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

def format_for_slack(draft):
    """Format a draft for Slack notification."""
    return f"""
📱 *iMessage Draft Ready for Review*

*From:* {draft['sender']}
*Chat:* {draft.get('chat', 'Direct')}
*Received:* {draft.get('received_at', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 *ORIGINAL MESSAGE:*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{draft['original_text']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ *DRAFT RESPONSE:*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{draft['draft_text']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Draft ID: {draft['id']} | iMessage ID: {draft['imessage_id']}

⚠️ *REMINDER:* This is a DRAFT only. You must manually copy and send it from Messages.app.
""".strip()

def main():
    parser = argparse.ArgumentParser(description="iMessage Draft Manager (NO SEND)")
    parser.add_argument("--list-pending", action="store_true", help="List pending iMessage drafts")
    parser.add_argument("--list-messages", action="store_true", help="List iMessages needing drafts")
    parser.add_argument("--format-slack", type=int, help="Format draft ID for Slack")
    
    args = parser.parse_args()
    
    conn = sqlite3.connect(DB_PATH)
    ensure_imessage_tables(conn)
    
    if args.list_pending:
        drafts = get_imessage_drafts(conn, 'pending')
        print(json.dumps({"success": True, "drafts": drafts}, indent=2))
    elif args.list_messages:
        messages = get_pending_imessages(conn)
        print(json.dumps({"success": True, "messages": messages}, indent=2))
    elif args.format_slack:
        cursor = conn.execute('''
            SELECT d.*, m.sender, m.chat, m.text as original_text, m.received_at
            FROM imessage_drafts d
            JOIN imessages m ON d.imessage_id = m.id
            WHERE d.id = ?
        ''', (args.format_slack,))
        row = cursor.fetchone()
        if row:
            draft = dict(zip([col[0] for col in cursor.description], row))
            print(format_for_slack(draft))
        else:
            print(json.dumps({"success": False, "error": "Draft not found"}))
    else:
        # Default: show status
        pending = get_imessage_drafts(conn, 'pending')
        messages = get_pending_imessages(conn)
        print(json.dumps({
            "success": True,
            "pending_drafts": len(pending),
            "messages_needing_drafts": len(messages),
            "note": "⛔ DRAFT ONLY - No send capability"
        }, indent=2))
    
    conn.close()

if __name__ == "__main__":
    main()
