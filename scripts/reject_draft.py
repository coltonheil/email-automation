#!/usr/bin/env python3
"""
Reject Draft
Mark a draft as rejected via CLI
"""

import os
import sys
import argparse

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Reject a draft response')
    parser.add_argument('draft_id', type=int, help='Draft ID to reject')
    parser.add_argument('--by', dest='rejected_by', default='user', help='Who rejected it')
    parser.add_argument('--reason', required=True, help='Rejection reason')
    parser.add_argument('--notes', help='Optional additional notes')
    parser.add_argument('--show', action='store_true', help='Show draft before rejecting')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    
    # Get draft details
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT d.*, e.subject, e.from_email
        FROM draft_responses d
        JOIN emails e ON d.email_id = e.id
        WHERE d.id = ?
    """, (args.draft_id,))
    
    draft = cursor.fetchone()
    
    if not draft:
        print(f"❌ Draft {args.draft_id} not found")
        sys.exit(1)
    
    # Show draft if requested
    if args.show:
        print("\n" + "="*70)
        print(f"DRAFT #{args.draft_id}")
        print("="*70)
        print(f"Subject: Re: {draft['subject']}")
        print(f"To: {draft['from_email']}")
        print(f"Status: {draft['status']}")
        print(f"Generated: {draft['created_at']}")
        print(f"Model: {draft['model_used']}")
        print("\n" + "-"*70)
        print("DRAFT TEXT:")
        print("-"*70)
        print(draft['draft_text'])
        print("="*70 + "\n")
        
        # Confirm
        confirm = input(f"Reject this draft (reason: {args.reason})? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ Cancelled")
            sys.exit(0)
    
    # Reject draft
    success = db.reject_draft(
        draft_id=args.draft_id,
        rejected_by=args.rejected_by,
        reason=args.reason,
        notes=args.notes
    )
    
    if success:
        print(f"✅ Draft {args.draft_id} rejected")
        print(f"   Reason: {args.reason}")
        if args.notes:
            print(f"   Notes: {args.notes}")
    else:
        print(f"❌ Failed to reject draft {args.draft_id}")
        sys.exit(1)
    
    db.close()


if __name__ == '__main__':
    main()
