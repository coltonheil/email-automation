#!/usr/bin/env python3
"""
Email Sync Script - Fetches emails and stores in SQLite database
Supports incremental syncing (only fetch new emails)
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from email_fetcher import EmailFetcher
from email_normalizer import EmailNormalizer
from priority_scorer import PriorityScorer
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Sync emails to database')
    parser.add_argument('--mode', choices=['unread', 'recent', 'all', 'incremental'], 
                        default='incremental', help='Sync mode')
    parser.add_argument('--limit', type=int, default=20, 
                        help='Max emails per account (default: 20)')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours to look back for mode=recent')
    parser.add_argument('--json', action='store_true',
                        help='Output JSON instead of summary')
    parser.add_argument('--cleanup', action='store_true',
                        help='Clean up old read emails (30+ days)')
    
    args = parser.parse_args()
    
    # Initialize database
    db = EmailDatabase()
    
    # Cleanup if requested
    if args.cleanup:
        deleted = db.cleanup_old_read_emails(days=30)
        print(f"🗑️  Cleaned up {deleted} old read emails")
    
    # Initialize fetchers
    fetcher = EmailFetcher()
    normalizer = EmailNormalizer()
    scorer = PriorityScorer()
    
    # Load account config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'accounts.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    total_fetched = 0
    total_new = 0
    
    # Process each account
    for provider_accounts in [config.get('gmail', []), config.get('outlook', []), config.get('instantly', [])]:
        for account in provider_accounts:
            provider = account['provider']
            account_id = account['composio_account_id']
            description = account.get('description', account['id'])
            
            if not args.json:
                print(f"📧 Syncing {description} ({provider})...", end=' ', flush=True)
            
            try:
                # Determine what to fetch
                if args.mode == 'incremental':
                    # Fetch only emails newer than last sync
                    last_sync = db.get_last_sync(account['id'])
                    if last_sync:
                        # Fetch emails from last 2 hours (to catch any we might have missed)
                        raw_emails = fetcher.fetch_recent(provider, account_id, hours=2, limit=args.limit)
                    else:
                        # First sync - fetch unread
                        raw_emails = fetcher.fetch_unread_only(provider, account_id, limit=args.limit)
                elif args.mode == 'unread':
                    raw_emails = fetcher.fetch_unread_only(provider, account_id, limit=args.limit)
                elif args.mode == 'recent':
                    raw_emails = fetcher.fetch_recent(provider, account_id, hours=args.hours, limit=args.limit)
                else:  # all
                    if provider == 'gmail':
                        raw_emails = fetcher.fetch_gmail(account_id, limit=args.limit)
                    elif provider == 'outlook':
                        raw_emails = fetcher.fetch_outlook(account_id, limit=args.limit)
                    elif provider == 'instantly':
                        raw_emails = fetcher.fetch_instantly(account_id, limit=args.limit)
                    else:
                        raw_emails = []
                
                # Normalize and score
                new_count = 0
                for raw_email in raw_emails:
                    normalized = normalizer.normalize(raw_email, provider, account['id'])
                    priority_score = scorer.score(normalized)
                    priority_category = scorer.categorize_priority(priority_score)
                    
                    normalized['priority_score'] = priority_score
                    normalized['priority_category'] = priority_category
                    
                    # Store in database
                    db.store_email(normalized)
                    new_count += 1
                
                total_fetched += len(raw_emails)
                total_new += new_count
                
                # Log sync
                db.log_sync(
                    account_id=account['id'],
                    emails_fetched=len(raw_emails),
                    new_emails=new_count,
                    status='completed'
                )
                
                if not args.json:
                    print(f"✅ {new_count} emails")
            
            except Exception as e:
                if not args.json:
                    print(f"❌ Error: {str(e)}")
                
                # Log failed sync
                db.log_sync(
                    account_id=account['id'],
                    emails_fetched=0,
                    new_emails=0,
                    status='failed',
                    error=str(e)
                )
    
    # Output results
    if args.json:
        # Return counts and recent emails
        recent_emails = db.get_emails_by_filter('all', limit=100)
        print(json.dumps({
            'success': True,
            'total_fetched': total_fetched,
            'total_new': total_new,
            'total_in_database': len(recent_emails),
            'synced_at': datetime.now().isoformat()
        }, indent=2))
    else:
        print(f"\n✅ Sync complete: {total_fetched} fetched, {total_new} new")
        
        # Show stats
        unread_count = len(db.get_unread_emails())
        urgent_count = len(db.get_urgent_unread_emails())
        print(f"📊 Database: {unread_count} unread, {urgent_count} urgent")
    
    db.close()


if __name__ == '__main__':
    main()
