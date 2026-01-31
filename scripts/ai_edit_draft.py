#!/usr/bin/env python3
"""
AI Edit Draft Script

Queues AI edit requests for processing by Clawdbot.
Reads JSON input from stdin, stores request in database queue.

Uses Clawdbot's Claude Max subscription - Clawdbot processes the queue.
"""

import json
import sys
import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'emails.db')

def ensure_queue_table(conn):
    """Create the AI edit queue table if it doesn't exist."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_edit_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id INTEGER NOT NULL,
            instruction TEXT NOT NULL,
            current_draft TEXT NOT NULL,
            original_email_json TEXT,
            status TEXT DEFAULT 'pending',
            result_text TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            processed_at TEXT,
            FOREIGN KEY (draft_id) REFERENCES draft_responses(id)
        )
    ''')
    conn.commit()

def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)
    
    draft_id = input_data.get('draft_id')
    instruction = input_data.get('instruction')
    current_draft = input_data.get('current_draft')
    original_email = input_data.get('original_email', {})
    
    if not instruction or not current_draft:
        print(json.dumps({"success": False, "error": "Missing instruction or current_draft"}))
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        ensure_queue_table(conn)
        
        now = datetime.now().isoformat()
        
        # Insert into queue
        cursor = conn.execute('''
            INSERT INTO ai_edit_queue (draft_id, instruction, current_draft, original_email_json, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (draft_id, instruction, current_draft, json.dumps(original_email), now))
        
        queue_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Return success with queue ID - Clawdbot will process this
        print(json.dumps({
            "success": True,
            "queued": True,
            "queue_id": queue_id,
            "draft_id": draft_id,
            "message": "Edit request queued. Processing in background..."
        }))
        
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()
