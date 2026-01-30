#!/usr/bin/env python3
"""
Auto-Draft Worker
Analyzes urgent emails and generates draft responses with sender context
Posts drafts to Slack #exec-approvals for manual review

SAFETY: This script NEVER sends emails. It only creates drafts for review.

Features robust error handling - continues processing even if individual emails fail.
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from database import EmailDatabase
from sender_analyzer import SenderAnalyzer
from draft_generator import DraftGenerator
from retry_utils import ErrorCollector, logger
from rate_limiter import RateLimiter
from sender_filter import SenderFilter


def main():
    parser = argparse.ArgumentParser(description='Auto-draft responses for urgent emails')
    parser.add_argument('--min-priority', type=int, default=80,
                        help='Minimum priority score to auto-draft (default: 80)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Max emails to process (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be drafted without actually drafting')
    parser.add_argument('--post-to-slack', action='store_true',
                        help='Post drafts to Slack #exec-approvals')
    parser.add_argument('--json', action='store_true',
                        help='Output JSON instead of text')
    
    args = parser.parse_args()
    
    # Initialize database
    db = EmailDatabase()
    
    # Get urgent unread emails
    urgent_emails = db.get_urgent_unread_emails()
    
    if not args.json:
        print(f"🔍 Found {len(urgent_emails)} urgent unread emails")
    
    # Filter by priority
    emails_to_draft = [
        email for email in urgent_emails 
        if email.get('priority_score', 0) >= args.min_priority
        and email.get('draft_id') is None  # Not already drafted
    ][:args.limit]
    
    if not args.json:
        print(f"📝 {len(emails_to_draft)} need drafts (priority >= {args.min_priority})")
    
    if not emails_to_draft:
        if not args.json:
            print("✅ No emails need drafts")
        return
    
    # Initialize analyzers
    analyzer = SenderAnalyzer(db)
    sender_filter = SenderFilter()
    
    # Initialize draft generator (uses Clawdbot + Claude Max subscription)
    generator = DraftGenerator(session_label="email-automation")
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(max_drafts_per_run=args.limit)
    rate_limiter.reset_run_counter()
    
    # Log filter stats
    filter_stats = sender_filter.get_stats()
    logger.info(f"Sender filter loaded: {filter_stats['skip_patterns']} skip patterns, "
                f"{filter_stats['always_draft_patterns']} VIP patterns")
    
    # Error collector for graceful handling
    errors = ErrorCollector()
    drafts_created = []
    
    logger.info(f"Starting auto-draft for {len(emails_to_draft)} emails")
    
    for email in emails_to_draft:
        sender_email = email.get('from_email')
        email_id = email.get('id')
        subject = email.get('subject', '(no subject)')
        
        if not args.json:
            print(f"\n📧 Processing: {subject[:60]}...")
            print(f"   From: {sender_email}")
        
        try:
            # Build sender context first (needed for filtering)
            if not args.json:
                print("   📊 Analyzing sender context...")
            
            context = analyzer.build_sender_context(sender_email, email)
            
            # Check sender filter (whitelist/blacklist)
            should_skip, filter_reason = sender_filter.should_skip_drafting(sender_email, context, email)
            
            if should_skip:
                if not args.json:
                    print(f"   🚫 Filtered: {filter_reason}")
                logger.info(f"Filtered email {email_id}: {filter_reason}")
                continue
            
            # Check rate limits
            can_draft, reason = rate_limiter.can_generate_draft(email_id, sender_email)
            
            if not can_draft:
                if not args.json:
                    print(f"   ⏭️  Rate limited: {reason}")
                logger.info(f"Rate limited email {email_id}: {reason}")
                continue
            
            if not args.dry_run:
                # Enforce rate limit delay
                rate_limiter.enforce_delay()
                # Generate draft
                if not args.json:
                    print("   ✍️  Generating draft with Claude Opus...")
                
                try:
                    draft_result = generator.generate_draft(
                        sender_context=context,
                        user_writing_style="professional and concise"
                    )
                    
                    draft_text = draft_result['draft_text']
                    model_used = draft_result['model_used']
                    
                    # Record API usage
                    rate_limiter.record_api_usage(
                        service='claude',
                        action='generate_draft',
                        success=True,
                        tokens_used=draft_result.get('prompt_tokens', 0) + draft_result.get('completion_tokens', 0),
                        metadata={'email_id': email_id, 'sender': sender_email}
                    )
                    
                    # Store draft in database
                    cursor = db.conn.cursor()
                    cursor.execute("""
                        INSERT INTO draft_responses (
                            email_id, draft_text, model_used, status
                        ) VALUES (?, ?, ?, 'pending')
                    """, (email_id, draft_text, model_used))
                    
                    draft_id = cursor.lastrowid
                    db.conn.commit()
                    
                    # Record draft generation
                    rate_limiter.record_draft_generated(email_id, sender_email, draft_id)
                
                except Exception as draft_error:
                    # Record failed API usage
                    rate_limiter.record_api_usage(
                        service='claude',
                        action='generate_draft',
                        success=False,
                        metadata={'email_id': email_id, 'sender': sender_email, 'error': str(draft_error)}
                    )
                    raise  # Re-raise to be caught by outer error handler
                
                if not args.json:
                    print(f"   ✅ Draft created (ID: {draft_id})")
                    print(f"   📝 Preview: {draft_text[:100]}...")
                
                # Prepare for Slack posting
                draft_info = {
                    'draft_id': draft_id,
                    'email_id': email_id,
                    'subject': subject,
                    'from_email': sender_email,
                    'from_name': context.get('sender_name', ''),
                    'priority_score': email.get('priority_score'),
                    'relationship_type': context.get('relationship_type'),
                    'draft_text': draft_text,
                    'model_used': model_used,
                }
                
                drafts_created.append(draft_info)
            else:
                # Dry run - just show what would happen
                if not args.json:
                    print(f"   [DRY RUN] Would generate draft for this email")
                    print(f"   Context: {context.get('relationship_type')} | "
                          f"{len(context.get('common_topics', []))} topics | "
                          f"{context.get('writing_style')} style")
        
        except Exception as e:
            # Collect error but continue processing other emails
            errors.add(f"Email {email_id} ({subject[:40]}...)", e)
            if not args.json:
                print(f"   ❌ Error: {str(e)} (continuing...)")
    
    # Report errors if any
    if errors.has_errors():
        logger.warning(f"Completed with {errors.count()} errors")
        if not args.json:
            print(f"\n⚠️  Completed with {errors.count()} errors (see logs/email-automation.log)")
    
    # Show usage summary
    if not args.json:
        usage = rate_limiter.get_usage_summary(hours=24)
        print(f"\n📊 API Usage (last 24 hours):")
        for service, stats in usage.get('services', {}).items():
            print(f"   {service}: {stats['calls']} calls, {stats['tokens']} tokens")
    
    # Output results
    if args.json:
        print(json.dumps({
            'success': True,
            'total_urgent': len(urgent_emails),
            'drafts_needed': len(emails_to_draft),
            'drafts_created': len(drafts_created),
            'drafts': drafts_created,
            'timestamp': datetime.now().isoformat()
        }, indent=2))
    else:
        print(f"\n✅ Auto-draft complete: {len(drafts_created)} drafts created")
        
        if args.post_to_slack and drafts_created:
            print("\n📤 Posting to Slack #exec-approvals...")
            post_drafts_to_slack(drafts_created)
    
    db.close()


def post_drafts_to_slack(drafts: list):
    """
    Post drafts to Slack #exec-approvals channel
    
    This will be called from Node.js/Clawdbot message tool
    For now, output instructions
    """
    print("\n" + "="*70)
    print("SLACK NOTIFICATION READY")
    print("="*70)
    
    for draft in drafts:
        print(f"\n🚨 URGENT EMAIL - Auto-Draft Ready")
        print(f"\nFrom: {draft['from_name']} <{draft['from_email']}>")
        print(f"Subject: {draft['subject']}")
        print(f"Priority: {draft['priority_score']}/100")
        print(f"Relationship: {draft['relationship_type'].replace('_', ' ').title()}")
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✍️  SUGGESTED DRAFT RESPONSE:")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"\n{draft['draft_text']}\n")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Model: {draft['model_used']}")
        print(f"Draft ID: {draft['draft_id']}")
        print(f"\n⚠️  REMINDER: This is a DRAFT only. You must manually send it.")
        print("="*70)


if __name__ == '__main__':
    main()
