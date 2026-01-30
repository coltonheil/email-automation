#!/usr/bin/env python3
"""
Cleanup Drafts
Delete old rejected/stale drafts
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Cleanup old drafts')
    parser.add_argument('--status', choices=['rejected', 'pending', 'all'], default='rejected',
                        help='Which drafts to clean up (default: rejected)')
    parser.add_argument('--older-than', type=int, default=7, help='Delete drafts older than N days (default: 7)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=args.older_than)).isoformat()
    
    conditions = ["created_at < ?"]
    params = [cutoff]
    
    if args.status != 'all':
        conditions.append("status = ?")
        params.append(args.status)
    
    where_clause = " AND ".join(conditions)
    
    # Count
    cursor.execute(f"SELECT COUNT(*) FROM draft_responses WHERE {where_clause}", params)
    count = cursor.fetchone()[0]
    
    print(f"\n🗑️  Found {count} drafts to delete")
    print(f"   Status: {args.status}")
    print(f"   Older than: {args.older_than} days")
    
    if count == 0:
        print("   Nothing to delete!")
        return
    
    if args.dry_run:
        print("\n[DRY RUN] Would delete these drafts:")
        cursor.execute(f"""
            SELECT d.id, d.status, d.created_at, e.subject
            FROM draft_responses d
            JOIN emails e ON d.email_id = e.id
            WHERE {where_clause}
            ORDER BY d.created_at DESC LIMIT 10
        """, params)
        for row in cursor.fetchall():
            print(f"   - Draft #{row[0]} ({row[1]}): Re: {row[3][:30]}...")
        if count > 10:
            print(f"   ... and {count - 10} more")
    else:
        # Delete approval history first
        cursor.execute(f"""
            DELETE FROM draft_approval_history 
            WHERE draft_id IN (SELECT id FROM draft_responses WHERE {where_clause})
        """, params)
        
        # Delete versions
        try:
            cursor.execute(f"""
                DELETE FROM draft_versions 
                WHERE draft_id IN (SELECT id FROM draft_responses WHERE {where_clause})
            """, params)
        except:
            pass
        
        # Delete drafts
        cursor.execute(f"DELETE FROM draft_responses WHERE {where_clause}", params)
        db.conn.commit()
        
        print(f"\n✅ Deleted {count} drafts")
    
    db.close()


if __name__ == '__main__':
    main()
