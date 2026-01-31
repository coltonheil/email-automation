#!/usr/bin/env python3
"""
Fetch Stale Unread iMessages - Messages unread for >2 hours

⛔ SAFETY: This script is READ-ONLY.
   It only reads from the Messages database.
   NO SEND CAPABILITY whatsoever.

Usage:
    python3 fetch_stale_imessages.py              # Default: >2 hours old
    python3 fetch_stale_imessages.py --hours 4   # >4 hours old
    python3 fetch_stale_imessages.py --queue     # Queue for Opus drafting
"""

import sqlite3
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Add paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'lib'))

# CRITICAL: Import send guard FIRST
from send_guard import SendBlockedError

# Messages database (READ ONLY)
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")
APPLE_EPOCH = datetime(2001, 1, 1)
DB_PATH = PROJECT_ROOT / "database" / "emails.db"


def apple_timestamp_to_datetime(ts):
    """Convert Apple's nanosecond timestamp to datetime."""
    if ts is None or ts == 0:
        return None
    seconds = ts / 1_000_000_000
    return APPLE_EPOCH + timedelta(seconds=seconds)


def get_stale_unread_messages(min_age_hours: float = 2.0, limit: int = 50):
    """
    Fetch messages that:
    - Are unread (is_read = 0)
    - Are from others (is_from_me = 0)
    - Are older than min_age_hours
    
    ⛔ READ ONLY - No send capability.
    
    Returns dict grouped by sender phone number.
    """
    if not os.path.exists(MESSAGES_DB):
        return {"success": False, "error": "Messages database not found"}
    
    try:
        # Calculate cutoff time
        cutoff = datetime.now() - timedelta(hours=min_age_hours)
        cutoff_apple = int((cutoff - APPLE_EPOCH).total_seconds() * 1_000_000_000)
        
        # Also set a max age (don't go back more than 7 days)
        max_age = datetime.now() - timedelta(days=7)
        max_age_apple = int((max_age - APPLE_EPOCH).total_seconds() * 1_000_000_000)
        
        # Open READ ONLY
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        query = """
        SELECT 
            m.rowid as message_id,
            m.guid as message_guid,
            m.text,
            m.date as timestamp,
            m.is_read,
            m.service,
            h.id as sender_phone,
            c.chat_identifier
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.rowid
        WHERE m.is_from_me = 0
          AND m.is_read = 0
          AND m.date < ?
          AND m.date > ?
          AND m.text IS NOT NULL
          AND m.text != ''
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor = conn.execute(query, (cutoff_apple, max_age_apple, limit))
        
        # Group by sender
        by_sender = defaultdict(list)
        
        for row in cursor:
            ts = apple_timestamp_to_datetime(row["timestamp"])
            if ts:
                phone = row["sender_phone"] or row["chat_identifier"] or "Unknown"
                by_sender[phone].append({
                    "id": row["message_id"],
                    "guid": row["message_guid"],
                    "text": row["text"],
                    "timestamp": ts.isoformat(),
                    "age_hours": (datetime.now() - ts).total_seconds() / 3600,
                    "service": row["service"] or "iMessage"
                })
        
        conn.close()
        
        # Look up contact names
        contact_names = {}
        try:
            from contacts_lookup import lookup_multiple
            phones = list(by_sender.keys())
            if phones:
                contact_names = lookup_multiple(phones)
        except:
            pass
        
        # Format results
        results = []
        for phone, messages in by_sender.items():
            results.append({
                "phone": phone,
                "contact_name": contact_names.get(phone),
                "message_count": len(messages),
                "oldest_message_hours": max(m["age_hours"] for m in messages),
                "messages": sorted(messages, key=lambda m: m["timestamp"])
            })
        
        # Sort by oldest message first
        results.sort(key=lambda r: r["oldest_message_hours"], reverse=True)
        
        return {
            "success": True,
            "min_age_hours": min_age_hours,
            "sender_count": len(results),
            "total_messages": sum(len(r["messages"]) for r in results),
            "senders": results,
            "note": "⛔ READ ONLY - These are draft candidates only"
        }
        
    except sqlite3.OperationalError as e:
        if "unable to open database" in str(e).lower():
            return {"success": False, "error": "Cannot access Messages database. Need Full Disk Access."}
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def queue_for_drafting(senders: list) -> dict:
    """
    Queue stale unread messages for Opus 4.5 draft generation.
    
    ⛔ QUEUES FOR DRAFTING ONLY - NO SENDING
    """
    from imessage_drafter import iMessageDrafter
    from imessage_context import build_conversation_context
    
    drafter = iMessageDrafter()
    queued = []
    errors = []
    
    for sender in senders:
        phone = sender["phone"]
        contact_name = sender.get("contact_name")
        
        try:
            # Build full context (last 30 messages)
            context = build_conversation_context(
                phone=phone,
                contact_name=contact_name,
                message_limit=30
            )
            
            # Queue for Opus processing
            result = drafter.generate_draft(context, use_opus=True)
            
            if result.success:
                queued.append({
                    "phone": phone,
                    "contact_name": contact_name,
                    "queue_id": result.queue_id,
                    "unread_count": len(sender["messages"])
                })
            else:
                errors.append({
                    "phone": phone,
                    "error": result.error
                })
                
        except Exception as e:
            errors.append({
                "phone": phone,
                "error": str(e)
            })
    
    return {
        "success": True,
        "queued": len(queued),
        "errors": len(errors),
        "items": queued,
        "error_details": errors if errors else None,
        "note": "⛔ QUEUED FOR DRAFTING ONLY - No messages will be sent"
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch stale unread iMessages (READ ONLY)")
    parser.add_argument("--hours", type=float, default=2.0, help="Minimum age in hours (default: 2)")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to fetch (default: 50)")
    parser.add_argument("--queue", action="store_true", help="Queue for Opus 4.5 drafting")
    
    args = parser.parse_args()
    
    # Fetch stale unread messages
    result = get_stale_unread_messages(min_age_hours=args.hours, limit=args.limit)
    
    if not result.get("success"):
        print(json.dumps(result, indent=2))
        return
    
    if args.queue and result.get("senders"):
        # Queue for Opus drafting
        queue_result = queue_for_drafting(result["senders"])
        print(json.dumps(queue_result, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
