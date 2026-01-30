#!/usr/bin/env python3
"""
Draft Stale Unread Emails
Auto-drafts responses for emails that have been unread for too long
(Default: 8 hours - indicates you need to respond but haven't)
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from database import EmailDatabase
from sender_analyzer import SenderAnalyzer
from draft_generator import DraftGenerator
from rate_limiter import RateLimiter
from sender_filter import SenderFilter
from retry_utils import ErrorCollector, logger


def main():
    parser = argparse.ArgumentParser(description='Draft responses for stale unread emails')
    parser.add_argument('--hours', type=int, default=8, help='Draft if unread longer than N hours (default: 8)')
    parser.add_argument('--limit', type=int, default=5, help='Max drafts to generate (default: 5)')
    parser.add_argument('--min-priority', type=int, default=40, help='Minimum priority (default: 40)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be drafted')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    
    # Calculate cutoff time
    cutoff = (datetime.now() - timedelta(hours=args.hours)).isoformat()
    
    if not args.json:
        print(f"\n⏰ Finding emails unread for {args.hours}+ hours...")
        print(f"   Cutoff: {cutoff[:16]}")
    
    # Find stale unread emails without drafts
    cursor.execute("""
        SELECT e.* FROM emails e
        LEFT JOIN draft_responses d ON e.id = d.email_id
        WHERE e.is_unread = 1
          AND e.received_at < ?
          AND e.priority_score >= ?
          AND d.id IS NULL
        ORDER BY e.priority_score DESC, e.received_at ASC
        LIMIT ?
    """, (cutoff, args.min_priority, args.limit * 2))  # Fetch extra for filtering
    
    columns = [desc[0] for desc in cursor.description]
    stale_emails = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    if not args.json:
        print(f"   Found {len(stale_emails)} stale unread emails")
    
    if not stale_emails:
        if not args.json:
            print("\n✅ No stale emails need drafts")
        return
    
    # Initialize tools
    analyzer = SenderAnalyzer(db)
    sender_filter = SenderFilter()
    rate_limiter = RateLimiter(max_drafts_per_run=args.limit)
    
    if not args.dry_run:
        generator = DraftGenerator(session_label="email-automation-stale")
    
    errors = ErrorCollector()
    drafts_created = []
    
    for email in stale_emails:
        if len(drafts_created) >= args.limit:
            break
        
        email_id = email['id']
        sender_email = email['from_email']
        subject = email['subject'] or '(no subject)'
        received_at = email['received_at']
        
        # Calculate hours since received
        try:
            received_dt = datetime.fromisoformat(received_at.replace('Z', '+00:00'))
            hours_ago = (datetime.now(received_dt.tzinfo) - received_dt).total_seconds() / 3600
        except:
            hours_ago = args.hours + 1
        
        if not args.json:
            print(f"\n📧 {subject[:50]}...")
            print(f"   From: {sender_email}")
            print(f"   Unread for: {hours_ago:.1f} hours")
            print(f"   Priority: {email['priority_score']}")
        
        # Check sender filter
        context = analyzer.build_sender_context(sender_email, email)
        should_skip, reason = sender_filter.should_skip_drafting(sender_email, context, email)
        
        if should_skip:
            if not args.json:
                print(f"   ⏭️  Skipping: {reason}")
            continue
        
        # Check rate limits
        can_draft, limit_reason = rate_limiter.can_generate_draft(email_id, sender_email)
        if not can_draft:
            if not args.json:
                print(f"   ⏭️  Rate limited: {limit_reason}")
            continue
        
        if args.dry_run:
            if not args.json:
                print(f"   [DRY RUN] Would generate draft")
            drafts_created.append({
                'email_id': email_id,
                'subject': subject,
                'sender': sender_email,
                'hours_unread': round(hours_ago, 1)
            })
            continue
        
        # Generate draft
        try:
            rate_limiter.enforce_delay()
            
            if not args.json:
                print(f"   ✍️  Generating draft...")
            
            draft_result = generator.generate_draft(
                sender_context=context,
                user_writing_style="professional and concise",
                additional_instructions=f"This email has been waiting for a response for {hours_ago:.0f} hours. Be helpful and apologize briefly for any delay if appropriate."
            )
            
            draft_text = draft_result['draft_text']
            
            # Save to database
            cursor.execute("""
                INSERT INTO draft_responses (email_id, draft_text, model_used, status)
                VALUES (?, ?, ?, 'pending')
            """, (email_id, draft_text, draft_result['model_used']))
            
            draft_id = cursor.lastrowid
            db.conn.commit()
            
            rate_limiter.record_draft_generated(email_id, sender_email, draft_id)
            rate_limiter.record_api_usage('claude', 'generate_draft_stale', True)
            
            if not args.json:
                print(f"   ✅ Draft created (ID: {draft_id})")
            
            drafts_created.append({
                'draft_id': draft_id,
                'email_id': email_id,
                'subject': subject,
                'sender': sender_email,
                'hours_unread': round(hours_ago, 1)
            })
            
        except Exception as e:
            errors.add(f"Email {email_id}", e)
            if not args.json:
                print(f"   ❌ Error: {e}")
    
    # Summary
    if args.json:
        import json
        print(json.dumps({
            'success': True,
            'stale_emails_found': len(stale_emails),
            'drafts_created': len(drafts_created),
            'drafts': drafts_created,
            'errors': errors.count()
        }, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"✅ Created {len(drafts_created)} drafts for stale emails")
        if errors.has_errors():
            print(f"⚠️  {errors.count()} errors occurred")
    
    db.close()


if __name__ == '__main__':
    main()
