#!/usr/bin/env python3
"""
Bulk Mark Read
Mark emails as read based on filters
"""

import os
import sys
import argparse
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Bulk mark emails as read')
    parser.add_argument('--from', dest='from_filter', help='Filter by sender (supports wildcards: *@example.com)')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--priority-below', type=int, help='Mark read if priority below this value')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be marked without doing it')
    
    args = parser.parse_args()
    
    if not any([args.from_filter, args.category, args.priority_below]):
        print("❌ Must specify at least one filter: --from, --category, or --priority-below")
        sys.exit(1)
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    
    # Build query
    conditions = ["is_unread = 1"]
    params = []
    
    if args.from_filter:
        # Convert wildcard to SQL LIKE pattern
        pattern = args.from_filter.replace('*', '%')
        conditions.append("from_email LIKE ?")
        params.append(pattern)
    
    if args.category:
        conditions.append("category = ?")
        params.append(args.category)
    
    if args.priority_below:
        conditions.append("priority_score < ?")
        params.append(args.priority_below)
    
    where_clause = " AND ".join(conditions)
    
    # Count
    cursor.execute(f"SELECT COUNT(*) FROM emails WHERE {where_clause}", params)
    count = cursor.fetchone()[0]
    
    print(f"\n📧 Found {count} unread emails matching filters")
    
    if count == 0:
        print("   Nothing to mark!")
        return
    
    if args.dry_run:
        print("\n[DRY RUN] Would mark these as read:")
        cursor.execute(f"""
            SELECT id, subject, from_email, priority_score
            FROM emails WHERE {where_clause}
            ORDER BY received_at DESC LIMIT 10
        """, params)
        for row in cursor.fetchall():
            print(f"   - {row[1][:40]} (from {row[2]}, priority {row[3]})")
        if count > 10:
            print(f"   ... and {count - 10} more")
    else:
        cursor.execute(f"UPDATE emails SET is_unread = 0 WHERE {where_clause}", params)
        db.conn.commit()
        print(f"\n✅ Marked {count} emails as read")
    
    db.close()


if __name__ == '__main__':
    main()
