#!/usr/bin/env python3
"""
Recalculate Priorities
Recalculate priority scores for all emails
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase
from priority_scorer import PriorityScorer


def main():
    parser = argparse.ArgumentParser(description='Recalculate email priority scores')
    parser.add_argument('--all', action='store_true', help='Recalculate all emails (default: only unscored)')
    parser.add_argument('--limit', type=int, default=1000, help='Max emails to process (default: 1000)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    scorer = PriorityScorer()
    
    # Get emails to process
    if args.all:
        cursor.execute("SELECT * FROM emails ORDER BY received_at DESC LIMIT ?", (args.limit,))
    else:
        cursor.execute("""
            SELECT * FROM emails 
            WHERE priority_score IS NULL OR priority_score = 50
            ORDER BY received_at DESC LIMIT ?
        """, (args.limit,))
    
    emails = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    print(f"\n📊 Processing {len(emails)} emails...")
    
    updated = 0
    changes = []
    
    for row in emails:
        email = dict(zip(columns, row))
        old_score = email.get('priority_score', 50)
        new_score = scorer.score(email)
        new_category = scorer.categorize_priority(new_score)
        
        if new_score != old_score:
            changes.append({
                'id': email['id'],
                'subject': email['subject'][:40],
                'old': old_score,
                'new': new_score,
                'category': new_category
            })
            
            if not args.dry_run:
                cursor.execute("""
                    UPDATE emails 
                    SET priority_score = ?, priority_category = ?
                    WHERE id = ?
                """, (new_score, new_category, email['id']))
                updated += 1
    
    if not args.dry_run:
        db.conn.commit()
    
    print(f"\n{'[DRY RUN] Would update' if args.dry_run else '✅ Updated'}: {len(changes)} emails")
    
    if changes:
        print("\nTop changes:")
        for c in sorted(changes, key=lambda x: abs(x['new'] - x['old']), reverse=True)[:10]:
            diff = c['new'] - c['old']
            arrow = '↑' if diff > 0 else '↓'
            print(f"   {c['subject']}: {c['old']} → {c['new']} ({arrow}{abs(diff)})")
    
    db.close()


if __name__ == '__main__':
    main()
