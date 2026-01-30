#!/usr/bin/env python3
"""
Batch Archive
Archive old read emails to reduce clutter
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Archive old read emails')
    parser.add_argument('--older-than', type=int, default=30, help='Archive emails older than N days (default: 30)')
    parser.add_argument('--category', help='Only archive specific category')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without doing it')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=args.older_than)).isoformat()
    
    # Build query
    conditions = ["is_unread = 0", "received_at < ?"]
    params = [cutoff]
    
    if args.category:
        conditions.append("category = ?")
        params.append(args.category)
    
    where_clause = " AND ".join(conditions)
    
    # Count emails to archive
    cursor.execute(f"SELECT COUNT(*) FROM emails WHERE {where_clause}", params)
    count = cursor.fetchone()[0]
    
    if not args.json:
        print(f"\n📦 Found {count} emails to archive")
        print(f"   Older than: {args.older_than} days")
        if args.category:
            print(f"   Category: {args.category}")
    
    if count == 0:
        if not args.json:
            print("   Nothing to archive!")
        return
    
    if args.dry_run:
        if not args.json:
            print("\n[DRY RUN] Would archive these emails:")
            cursor.execute(f"""
                SELECT id, subject, from_email, received_at, category
                FROM emails WHERE {where_clause}
                ORDER BY received_at DESC LIMIT 10
            """, params)
            for row in cursor.fetchall():
                print(f"   - {row[1][:50]} (from {row[2]}, {row[3][:10]})")
            if count > 10:
                print(f"   ... and {count - 10} more")
    else:
        # Create archive table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails_archive (
                id INTEGER PRIMARY KEY,
                original_id INTEGER,
                archived_at TEXT DEFAULT (datetime('now')),
                data TEXT
            )
        """)
        
        # Archive emails
        cursor.execute(f"""
            INSERT INTO emails_archive (original_id, data)
            SELECT id, json_object(
                'subject', subject,
                'from_email', from_email,
                'received_at', received_at,
                'category', category
            )
            FROM emails WHERE {where_clause}
        """, params)
        
        # Delete archived emails
        cursor.execute(f"DELETE FROM emails WHERE {where_clause}", params)
        
        db.conn.commit()
        
        if not args.json:
            print(f"\n✅ Archived {count} emails")
    
    db.close()


if __name__ == '__main__':
    main()
