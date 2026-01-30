#!/usr/bin/env python3
"""
Store a draft in the database and optionally post to Slack
Called by Clawdbot after generating a draft
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Store a draft response')
    parser.add_argument('--email-id', required=True, help='Email ID to draft for')
    parser.add_argument('--draft', required=True, help='Draft text')
    parser.add_argument('--model', default='claude-opus', help='Model used')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    
    # Get email info
    conn = db.conn
    cursor = conn.cursor()
    cursor.execute("SELECT from_email, from_name, subject FROM emails WHERE id = ?", (args.email_id,))
    email = cursor.fetchone()
    
    if not email:
        print(f"Error: Email {args.email_id} not found")
        sys.exit(1)
    
    from_email, from_name, subject = email
    
    # Store draft
    cursor.execute("""
        INSERT INTO draft_responses (email_id, draft_text, model_used, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    """, (args.email_id, args.draft, args.model, datetime.now().isoformat()))
    
    draft_id = cursor.lastrowid
    conn.commit()
    
    if args.json:
        print(json.dumps({
            'draft_id': draft_id,
            'email_id': args.email_id,
            'from': from_email,
            'subject': subject,
            'status': 'stored'
        }))
    else:
        print(f"✅ Draft #{draft_id} stored for: {subject[:50]}")
        print(f"   From: {from_name} <{from_email}>")
    
    return draft_id


if __name__ == '__main__':
    main()
