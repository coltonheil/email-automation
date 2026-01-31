#!/usr/bin/env python3
"""
Process AI Edit Queue

Called by Clawdbot to process pending AI edit requests.
Outputs the edit instruction and context for Clawdbot to process.

Usage:
  python3 process_ai_edit_queue.py           # Check for pending items
  python3 process_ai_edit_queue.py --complete <queue_id> "<new_draft_text>"  # Mark complete
  python3 process_ai_edit_queue.py --fail <queue_id> "<error_message>"       # Mark failed
"""

import json
import sys
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'emails.db')

def get_pending_items():
    """Get all pending AI edit requests."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT * FROM ai_edit_queue 
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 5
    ''')
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def mark_processing(queue_id):
    """Mark an item as processing."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        UPDATE ai_edit_queue 
        SET status = 'processing'
        WHERE id = ?
    ''', (queue_id,))
    conn.commit()
    conn.close()

def mark_completed(queue_id, new_draft_text):
    """Mark an item as completed with the result."""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    
    # Get the draft_id first
    cursor = conn.execute('SELECT draft_id, instruction FROM ai_edit_queue WHERE id = ?', (queue_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    draft_id, instruction = row
    
    # Update queue item
    conn.execute('''
        UPDATE ai_edit_queue 
        SET status = 'completed', result_text = ?, processed_at = ?
        WHERE id = ?
    ''', (new_draft_text, now, queue_id))
    
    # Update the actual draft
    conn.execute('''
        UPDATE draft_responses
        SET edited_text = ?, model_used = 'claude-opus'
        WHERE id = ?
    ''', (new_draft_text, draft_id))
    
    # Log the edit
    conn.execute('''
        INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes)
        VALUES (?, 'ai_edited', 'clawdbot', ?, ?)
    ''', (draft_id, now, instruction))
    
    conn.commit()
    conn.close()
    return True

def mark_failed(queue_id, error_message):
    """Mark an item as failed."""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.execute('''
        UPDATE ai_edit_queue 
        SET status = 'failed', error_message = ?, processed_at = ?
        WHERE id = ?
    ''', (error_message, now, queue_id))
    conn.commit()
    conn.close()

def main():
    args = sys.argv[1:]
    
    if len(args) >= 2 and args[0] == '--complete':
        queue_id = int(args[1])
        new_draft = args[2] if len(args) > 2 else sys.stdin.read().strip()
        if mark_completed(queue_id, new_draft):
            print(json.dumps({"success": True, "action": "completed", "queue_id": queue_id}))
        else:
            print(json.dumps({"success": False, "error": "Queue item not found"}))
        return
    
    if len(args) >= 3 and args[0] == '--fail':
        queue_id = int(args[1])
        error_msg = args[2]
        mark_failed(queue_id, error_msg)
        print(json.dumps({"success": True, "action": "failed", "queue_id": queue_id}))
        return
    
    if len(args) >= 2 and args[0] == '--processing':
        queue_id = int(args[1])
        mark_processing(queue_id)
        print(json.dumps({"success": True, "action": "processing", "queue_id": queue_id}))
        return
    
    # Default: get pending items
    items = get_pending_items()
    
    if not items:
        print(json.dumps({"success": True, "pending": 0, "items": []}))
        return
    
    # Format for Clawdbot processing
    output = {
        "success": True,
        "pending": len(items),
        "items": []
    }
    
    for item in items:
        original_email = json.loads(item.get('original_email_json', '{}'))
        output["items"].append({
            "queue_id": item['id'],
            "draft_id": item['draft_id'],
            "instruction": item['instruction'],
            "current_draft": item['current_draft'],
            "original_email": original_email,
            "created_at": item['created_at']
        })
    
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
