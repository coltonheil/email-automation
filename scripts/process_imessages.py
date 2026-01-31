#!/usr/bin/env python3
"""
Process Unread iMessages - Fetch and Queue for Draft Generation

⛔ SAFETY: This script is READ-ONLY for iMessages.
   It only reads messages and queues them for draft generation.
   All drafts go to Slack for human review.
   NO SENDING CAPABILITY.

Usage:
    python3 process_imessages.py                    # Process unread messages
    python3 process_imessages.py --hours 24         # Last 24 hours only
    python3 process_imessages.py --dry-run          # Show what would be processed
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'lib'))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

# Import send guard FIRST
from send_guard import SendBlockedError

# Import fetcher
from fetch_imessages import get_unread_messages, get_conversation_context

DB_PATH = PROJECT_ROOT / 'database' / 'emails.db'

def ensure_tables(conn):
    """Ensure iMessage tables exist."""
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
            has_draft INTEGER DEFAULT 0,
            needs_response INTEGER DEFAULT 1
        )
    ''')
    
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
            model_used TEXT DEFAULT 'clawdbot',
            FOREIGN KEY (imessage_id) REFERENCES imessages(id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS imessage_draft_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imessage_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT,
            error_message TEXT,
            FOREIGN KEY (imessage_id) REFERENCES imessages(id)
        )
    ''')
    
    conn.commit()

def store_message(conn, msg):
    """Store a message in the database if not already present."""
    cursor = conn.execute(
        'SELECT id FROM imessages WHERE message_guid = ?',
        (msg['guid'],)
    )
    existing = cursor.fetchone()
    
    if existing:
        return existing[0], False  # Already exists
    
    cursor = conn.execute('''
        INSERT INTO imessages (message_guid, sender, chat, text, received_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (msg['guid'], msg['sender'], msg.get('chat'), msg['text'], msg.get('timestamp')))
    
    conn.commit()
    return cursor.lastrowid, True  # Newly inserted

def queue_for_drafting(conn, imessage_id):
    """Add message to draft generation queue."""
    # Check if already queued
    cursor = conn.execute(
        'SELECT id FROM imessage_draft_queue WHERE imessage_id = ? AND status = ?',
        (imessage_id, 'pending')
    )
    if cursor.fetchone():
        return None  # Already queued
    
    cursor = conn.execute('''
        INSERT INTO imessage_draft_queue (imessage_id, status)
        VALUES (?, 'pending')
    ''', (imessage_id,))
    
    conn.commit()
    return cursor.lastrowid

def get_pending_queue(conn, limit=10):
    """Get messages pending draft generation."""
    cursor = conn.execute('''
        SELECT q.id as queue_id, q.imessage_id, m.sender, m.chat, m.text, m.received_at
        FROM imessage_draft_queue q
        JOIN imessages m ON q.imessage_id = m.id
        WHERE q.status = 'pending'
        ORDER BY q.created_at ASC
        LIMIT ?
    ''', (limit,))
    
    return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

def main():
    parser = argparse.ArgumentParser(description="Process unread iMessages (READ ONLY)")
    parser.add_argument("--hours", type=int, default=48, help="Hours to look back (default: 48)")
    parser.add_argument("--limit", type=int, default=20, help="Max messages to process (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--show-queue", action="store_true", help="Show pending draft queue")
    
    args = parser.parse_args()
    
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)
    
    if args.show_queue:
        queue = get_pending_queue(conn, limit=50)
        print(json.dumps({
            "success": True,
            "pending": len(queue),
            "items": queue
        }, indent=2))
        conn.close()
        return
    
    # Fetch unread messages
    result = get_unread_messages(limit=args.limit, hours_back=args.hours)
    
    if not result.get('success'):
        print(json.dumps(result))
        conn.close()
        return
    
    messages = result.get('messages', [])
    
    if args.dry_run:
        print(json.dumps({
            "success": True,
            "dry_run": True,
            "would_process": len(messages),
            "messages": [
                {"sender": m['sender'], "preview": m['text'][:50] + "..."}
                for m in messages
            ]
        }, indent=2))
        conn.close()
        return
    
    # Process each message
    new_messages = 0
    queued = 0
    
    for msg in messages:
        msg_id, is_new = store_message(conn, msg)
        
        if is_new:
            new_messages += 1
            queue_id = queue_for_drafting(conn, msg_id)
            if queue_id:
                queued += 1
    
    # Get current queue status
    pending_queue = get_pending_queue(conn)
    
    conn.close()
    
    print(json.dumps({
        "success": True,
        "fetched": len(messages),
        "new_messages": new_messages,
        "queued_for_drafting": queued,
        "total_pending": len(pending_queue),
        "note": "⛔ READ ONLY - Drafts will be generated by Clawdbot and posted to Slack"
    }, indent=2))

if __name__ == "__main__":
    main()
