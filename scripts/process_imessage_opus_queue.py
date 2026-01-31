#!/usr/bin/env python3
"""
Process iMessage Opus Queue - For Clawdbot to generate drafts

⛔⛔⛔ CRITICAL SAFETY: DRAFT GENERATION ONLY ⛔⛔⛔

This script:
- Reads pending queue items
- Outputs prompts for Clawdbot/Opus 4.5 to process
- Stores generated drafts in database
- NEVER sends any message

Clawdbot runs this script, generates drafts using Opus 4.5,
then calls --complete to store the result.

Usage:
    python3 process_imessage_opus_queue.py                    # Show pending
    python3 process_imessage_opus_queue.py --next             # Get next item for processing
    python3 process_imessage_opus_queue.py --complete <id> "<draft_json>"
    python3 process_imessage_opus_queue.py --fail <id> "<error>"
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'lib'))

# CRITICAL: Import send guard
from send_guard import SendBlockedError

from imessage_drafter import (
    get_pending_opus_queue,
    complete_opus_queue_item,
    fail_opus_queue_item,
    format_for_slack
)

import sqlite3
DB_PATH = PROJECT_ROOT / "database" / "emails.db"


def get_queue_status():
    """Get current queue status."""
    conn = sqlite3.connect(DB_PATH)
    
    # Count by status
    cursor = conn.execute('''
        SELECT status, COUNT(*) as count
        FROM imessage_opus_queue
        GROUP BY status
    ''')
    
    counts = {row[0]: row[1] for row in cursor}
    conn.close()
    
    return {
        "pending": counts.get("pending", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0)
    }


def get_next_item():
    """Get the next pending item for Clawdbot to process."""
    items = get_pending_opus_queue(limit=1)
    
    if not items:
        return {"success": True, "pending": 0, "item": None}
    
    item = items[0]
    
    # Mark as processing
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE imessage_opus_queue SET status = 'processing' WHERE id = ?",
        (item["id"],)
    )
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "pending": 1,
        "item": {
            "queue_id": item["id"],
            "phone": item["phone"],
            "contact_name": item["contact_name"],
            "prompt": item["prompt"],
            "context": json.loads(item["context_json"]) if item["context_json"] else None
        },
        "note": "⛔ GENERATE DRAFT ONLY - Do not send any message"
    }


def complete_item(queue_id: int, draft_json: str):
    """
    Complete a queue item with the generated draft.
    
    ⛔ STORES DRAFT ONLY - NO SENDING
    """
    try:
        # Parse draft messages
        draft_messages = json.loads(draft_json)
        if isinstance(draft_messages, str):
            draft_messages = [draft_messages]
        
        # Store the draft
        draft_id = complete_opus_queue_item(queue_id, draft_messages)
        
        # Get draft details for Slack notification
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT phone, contact_name FROM imessage_drafts WHERE id = ?",
            (draft_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        return {
            "success": True,
            "action": "completed",
            "queue_id": queue_id,
            "draft_id": draft_id,
            "phone": row["phone"] if row else None,
            "contact_name": row["contact_name"] if row else None,
            "message_count": len(draft_messages),
            "draft_preview": draft_messages[0][:100] + "..." if draft_messages else None,
            "note": "⛔ DRAFT STORED - Must be sent manually from Messages.app"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def fail_item(queue_id: int, error_message: str):
    """Mark a queue item as failed."""
    fail_opus_queue_item(queue_id, error_message)
    
    return {
        "success": True,
        "action": "failed",
        "queue_id": queue_id,
        "error": error_message
    }


def get_recent_drafts(limit: int = 10):
    """Get recently generated drafts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT * FROM imessage_drafts
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    drafts = []
    for row in cursor:
        draft = dict(row)
        draft["draft_messages"] = json.loads(draft["draft_messages"]) if draft["draft_messages"] else []
        drafts.append(draft)
    
    conn.close()
    
    return {
        "success": True,
        "drafts": drafts
    }


def main():
    parser = argparse.ArgumentParser(description="Process iMessage Opus Queue (DRAFT ONLY)")
    parser.add_argument("--next", action="store_true", help="Get next item for processing")
    parser.add_argument("--complete", type=int, metavar="ID", help="Complete queue item with draft")
    parser.add_argument("--fail", type=int, metavar="ID", help="Mark queue item as failed")
    parser.add_argument("--drafts", action="store_true", help="Show recent drafts")
    parser.add_argument("draft_json", nargs="?", help="Draft messages JSON (for --complete)")
    parser.add_argument("error_message", nargs="?", help="Error message (for --fail)")
    
    args = parser.parse_args()
    
    if args.next:
        result = get_next_item()
    elif args.complete is not None:
        if not args.draft_json:
            print(json.dumps({"success": False, "error": "Draft JSON required"}))
            return
        result = complete_item(args.complete, args.draft_json)
    elif args.fail is not None:
        error_msg = args.draft_json or args.error_message or "Unknown error"
        result = fail_item(args.fail, error_msg)
    elif args.drafts:
        result = get_recent_drafts()
    else:
        # Default: show status and pending items
        status = get_queue_status()
        pending_items = get_pending_opus_queue(limit=5)
        
        result = {
            "success": True,
            "status": status,
            "pending_items": [
                {
                    "queue_id": item["id"],
                    "phone": item["phone"],
                    "contact_name": item["contact_name"],
                    "created_at": item["created_at"]
                }
                for item in pending_items
            ],
            "note": "⛔ DRAFT GENERATION ONLY - No messages will be sent"
        }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
