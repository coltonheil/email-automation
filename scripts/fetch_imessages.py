#!/usr/bin/env python3
"""
Fetch Unread iMessages - READ ONLY

⛔ SAFETY: This script has NO send capability.
   It only READS from the Messages database.
   All responses are DRAFTS that go to Slack for human review.

Reads from ~/Library/Messages/chat.db (requires Full Disk Access)
"""

import sqlite3
import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add lib to path for send_guard
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

# CRITICAL: Import send guard to block any send operations
try:
    from send_guard import guard_applescript, SendBlockedError
except ImportError:
    # If send_guard not available, define a local block
    class SendBlockedError(Exception):
        pass
    def guard_applescript(script):
        if 'send' in script.lower():
            raise SendBlockedError("Send operations are blocked")

# Messages database location
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Apple's epoch starts at 2001-01-01
APPLE_EPOCH = datetime(2001, 1, 1)

def apple_timestamp_to_datetime(ts):
    """Convert Apple's nanosecond timestamp to datetime."""
    if ts is None or ts == 0:
        return None
    # Timestamps are in nanoseconds since 2001-01-01
    seconds = ts / 1_000_000_000
    return APPLE_EPOCH + timedelta(seconds=seconds)

def format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_unread_messages(limit=50, hours_back=48):
    """
    Fetch unread messages from the Messages database.
    
    READ ONLY - No send capability.
    """
    if not os.path.exists(MESSAGES_DB):
        return {
            "success": False,
            "error": f"Messages database not found at {MESSAGES_DB}. Need Full Disk Access."
        }
    
    try:
        # Connect read-only
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate cutoff time
        cutoff = datetime.now() - timedelta(hours=hours_back)
        cutoff_apple = int((cutoff - APPLE_EPOCH).total_seconds() * 1_000_000_000)
        
        # Query for unread messages (is_read = 0, is_from_me = 0)
        query = """
        SELECT 
            m.rowid as message_id,
            m.guid as message_guid,
            m.text,
            m.date as timestamp,
            m.is_read,
            m.is_from_me,
            m.service,
            h.id as sender_id,
            h.uncanonicalized_id as sender_raw,
            c.chat_identifier,
            c.display_name as chat_name
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.rowid
        WHERE m.is_from_me = 0
          AND m.is_read = 0
          AND m.date > ?
          AND m.text IS NOT NULL
          AND m.text != ''
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (cutoff_apple, limit))
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            msg = {
                "id": row["message_id"],
                "guid": row["message_guid"],
                "text": row["text"],
                "timestamp": format_datetime(apple_timestamp_to_datetime(row["timestamp"])),
                "sender": row["sender_id"] or row["sender_raw"] or "Unknown",
                "chat": row["chat_identifier"] or row["chat_name"] or "Unknown",
                "service": row["service"] or "iMessage"
            }
            messages.append(msg)
        
        conn.close()
        
        return {
            "success": True,
            "count": len(messages),
            "messages": messages,
            "note": "READ ONLY - No send capability. Drafts only."
        }
        
    except sqlite3.OperationalError as e:
        if "unable to open database file" in str(e).lower():
            return {
                "success": False,
                "error": "Cannot access Messages database. Grant Full Disk Access to Terminal/Python."
            }
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_conversation_context(sender_id, limit=10):
    """
    Get recent conversation history with a sender for context.
    
    READ ONLY - No send capability.
    """
    if not os.path.exists(MESSAGES_DB):
        return {"success": False, "error": "Messages database not found"}
    
    try:
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
        SELECT 
            m.text,
            m.date as timestamp,
            m.is_from_me,
            h.id as sender_id
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        WHERE (h.id = ? OR h.uncanonicalized_id = ?)
          AND m.text IS NOT NULL
          AND m.text != ''
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (sender_id, sender_id, limit))
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            messages.append({
                "text": row["text"],
                "timestamp": format_datetime(apple_timestamp_to_datetime(row["timestamp"])),
                "is_from_me": bool(row["is_from_me"]),
                "sender": "Me" if row["is_from_me"] else row["sender_id"]
            })
        
        conn.close()
        
        # Reverse to chronological order
        messages.reverse()
        
        return {
            "success": True,
            "sender": sender_id,
            "messages": messages
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """
    CLI interface for fetching iMessages.
    
    Usage:
        python3 fetch_imessages.py                    # Get unread messages
        python3 fetch_imessages.py --context +1234   # Get conversation context
        python3 fetch_imessages.py --hours 24        # Unread in last 24 hours
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch unread iMessages (READ ONLY)")
    parser.add_argument("--context", help="Get conversation context for sender ID")
    parser.add_argument("--hours", type=int, default=48, help="Hours to look back (default: 48)")
    parser.add_argument("--limit", type=int, default=50, help="Max messages (default: 50)")
    
    args = parser.parse_args()
    
    if args.context:
        result = get_conversation_context(args.context, args.limit)
    else:
        result = get_unread_messages(args.limit, args.hours)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
