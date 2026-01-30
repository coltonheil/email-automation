#!/usr/bin/env python3
"""
List emails that need drafts (not automated, not already drafted)
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


# Patterns to skip (automated/newsletters)
SKIP_PATTERNS = [
    'noreply', 'no-reply', 'donotreply', 'no_reply', 'notifications', 
    'marketing', 'newsletter', 'updates@', 'alerts@',
    '@t.delta.com', '@services.', '@mail.instagram.com',
    '@linkedin.com', '@uber.com', 'searchfunder.com',
    '@vercel.com', '@redfin.com', '@render.com',
    '@google.com', '@shopify.com', '@github.com',
    '@railway.app', '@chase.com', '@discover.com',
    '@notify.railway.app', '@mcmap.chase.com', '@insideapple.apple.com',
    '@lovable.dev', '@slack.com', '@slack.email', '@slackhq.com'
]


def needs_draft(email):
    """Check if email needs a human-written draft (not automated)"""
    from_email = email.get('from_email', '').lower()
    
    for pattern in SKIP_PATTERNS:
        if pattern.lower() in from_email:
            return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description='List emails needing drafts')
    parser.add_argument('--min-priority', type=int, default=60, help='Min priority')
    parser.add_argument('--limit', type=int, default=10, help='Max emails')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    conn = db.conn
    cursor = conn.cursor()
    
    # Get unread emails without drafts
    cursor.execute("""
        SELECT e.id, e.from_email, e.from_name, e.subject, e.snippet, e.priority_score, e.received_at
        FROM emails e
        LEFT JOIN draft_responses dr ON e.id = dr.email_id
        WHERE e.is_unread = 1 
          AND dr.id IS NULL
          AND e.priority_score >= ?
        ORDER BY e.priority_score DESC, e.received_at DESC
        LIMIT ?
    """, (args.min_priority, args.limit * 3))  # Fetch extra to filter
    
    emails = cursor.fetchall()
    
    # Filter out automated emails
    pending = []
    for row in emails:
        email = {
            'id': row[0],
            'from_email': row[1],
            'from_name': row[2],
            'subject': row[3],
            'snippet': row[4][:200] if row[4] else '',
            'priority_score': row[5],
            'received_at': row[6]
        }
        if needs_draft(email):
            pending.append(email)
            if len(pending) >= args.limit:
                break
    
    if args.json:
        print(json.dumps(pending, indent=2))
    else:
        print(f"📧 {len(pending)} emails need drafts:\n")
        for email in pending:
            print(f"ID: {email['id']}")
            print(f"From: {email['from_name']} <{email['from_email']}>")
            print(f"Subject: {email['subject']}")
            print(f"Priority: {email['priority_score']}")
            print(f"Preview: {email['snippet'][:100]}...")
            print("-" * 50)


if __name__ == '__main__':
    main()
