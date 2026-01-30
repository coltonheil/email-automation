#!/usr/bin/env python3
"""
Draft History
View approval history for a draft
"""

import os
import sys
import argparse
import json

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='View draft approval history')
    parser.add_argument('draft_id', type=int, help='Draft ID')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
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
    
    # Get history
    history = db.get_draft_history(args.draft_id)
    
    if args.json:
        # JSON output
        output = {
            'draft_id': args.draft_id,
            'subject': draft['subject'],
            'from_email': draft['from_email'],
            'status': draft['status'],
            'created_at': draft['created_at'],
            'history': history
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("\n" + "="*70)
        print(f"DRAFT #{args.draft_id} - HISTORY")
        print("="*70)
        print(f"Subject: Re: {draft['subject']}")
        print(f"To: {draft['from_email']}")
        print(f"Status: {draft['status']}")
        print(f"Created: {draft['created_at']}")
        print(f"Model: {draft['model_used']}")
        
        if draft['approved_at']:
            print(f"✅ Approved: {draft['approved_at']} by {draft['approved_by']}")
        
        if draft['rejected_at']:
            print(f"❌ Rejected: {draft['rejected_at']} by {draft['rejected_by']}")
            if draft['rejection_reason']:
                print(f"   Reason: {draft['rejection_reason']}")
        
        if draft['sent_at']:
            print(f"📧 Sent: {draft['sent_at']} via {draft['sent_via']}")
        
        if draft['feedback_score']:
            print(f"⭐ Rating: {draft['feedback_score']}/5")
            if draft['feedback_notes']:
                print(f"   Feedback: {draft['feedback_notes']}")
        
        print("\n" + "-"*70)
        print("TIMELINE:")
        print("-"*70)
        
        if not history:
            print("(No history recorded)")
        else:
            for entry in history:
                action_emoji = {
                    'approved': '✅',
                    'rejected': '❌',
                    'edited': '✏️',
                    'sent': '📧',
                    'rated': '⭐'
                }.get(entry['action'], '•')
                
                print(f"\n{action_emoji} {entry['action'].upper()}")
                print(f"   Time: {entry['performed_at']}")
                print(f"   By: {entry['performed_by']}")
                
                if entry['notes']:
                    print(f"   Notes: {entry['notes']}")
                
                if entry['metadata']:
                    try:
                        metadata = json.loads(entry['metadata'])
                        print(f"   Metadata: {metadata}")
                    except:
                        pass
        
        print("\n" + "="*70 + "\n")
    
    db.close()


if __name__ == '__main__':
    main()
