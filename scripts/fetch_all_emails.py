#!/usr/bin/env python3
"""
Unified Email Fetcher - Aggregates emails from all 8 inboxes

Fetches from:
- 1 Gmail account
- 3 Outlook accounts  
- 1 Instantly workspace (4 sending accounts)

Outputs a unified, prioritized triage queue.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from email_fetcher import EmailFetcher
from email_normalizer import EmailNormalizer
from priority_scorer import PriorityScorer


class UnifiedEmailAggregator:
    """Aggregates emails from all connected accounts"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize aggregator
        
        Args:
            config_path: Path to accounts.json config file
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'config', 
                'accounts.json'
            )
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.fetcher = EmailFetcher()
        self.normalizer = EmailNormalizer()
        self.scorer = PriorityScorer()
        
        self.emails = []
        self.seen_dedup_keys = set()
    
    def fetch_all(self, mode: str = 'unread', hours: int = None, limit_per_account: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch emails from all accounts
        
        Args:
            mode: 'unread', 'recent', or 'all'
            hours: If mode='recent', how many hours to look back
            limit_per_account: Max emails per account
            
        Returns:
            List of normalized, scored emails
        """
        self.emails = []
        self.seen_dedup_keys = set()
        
        print(f"🔍 Fetching emails (mode: {mode}, limit: {limit_per_account}/account)...\n")
        
        # Fetch from Gmail accounts
        for account in self.config.get('gmail', []):
            self._fetch_from_account(account, mode, hours, limit_per_account)
        
        # Fetch from Outlook accounts
        for account in self.config.get('outlook', []):
            self._fetch_from_account(account, mode, hours, limit_per_account)
        
        # Fetch from Instantly
        for account in self.config.get('instantly', []):
            self._fetch_from_account(account, mode, hours, limit_per_account)
        
        # Sort by priority score (highest first)
        self.emails.sort(key=lambda e: e['priority_score'], reverse=True)
        
        print(f"\n✅ Total emails fetched: {len(self.emails)}")
        print(f"📊 Breakdown: Urgent={self._count_by_category('urgent')}, Normal={self._count_by_category('normal')}, Low={self._count_by_category('low')}\n")
        
        return self.emails
    
    def _fetch_from_account(self, account: Dict[str, Any], mode: str, hours: int, limit: int):
        """Fetch emails from a single account"""
        provider = account['provider']
        account_id = account['composio_account_id']
        description = account.get('description', account['id'])
        
        print(f"📧 Fetching from {description} ({provider})...", end=' ')
        
        try:
            # Fetch based on mode
            if mode == 'unread':
                raw_emails = self.fetcher.fetch_unread_only(provider, account_id, limit=limit)
            elif mode == 'recent':
                hours = hours or 24
                raw_emails = self.fetcher.fetch_recent(provider, account_id, hours=hours, limit=limit)
            elif mode == 'all':
                if provider == 'gmail':
                    raw_emails = self.fetcher.fetch_gmail(account_id, limit=limit)
                elif provider == 'outlook':
                    raw_emails = self.fetcher.fetch_outlook(account_id, limit=limit)
                elif provider == 'instantly':
                    raw_emails = self.fetcher.fetch_instantly(account_id, limit=limit)
                else:
                    raw_emails = []
            else:
                print(f"❌ Unknown mode: {mode}")
                return
            
            # Normalize and score each email
            added_count = 0
            for raw_email in raw_emails:
                normalized = self.normalizer.normalize(raw_email, provider, account['id'])
                
                # Deduplicate
                dedup_key = self.normalizer.generate_dedup_key(normalized)
                if dedup_key in self.seen_dedup_keys:
                    continue
                self.seen_dedup_keys.add(dedup_key)
                
                # Score priority
                priority_score = self.scorer.score(normalized)
                priority_category = self.scorer.categorize_priority(priority_score)
                
                normalized['priority_score'] = priority_score
                normalized['priority_category'] = priority_category
                
                self.emails.append(normalized)
                added_count += 1
            
            print(f"✅ {added_count} emails")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def _count_by_category(self, category: str) -> int:
        """Count emails in a priority category"""
        return sum(1 for e in self.emails if e.get('priority_category') == category)
    
    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get emails in a specific priority category"""
        return [e for e in self.emails if e.get('priority_category') == category]
    
    def save_to_json(self, output_path: str):
        """Save aggregated emails to JSON file"""
        output_data = {
            'generated_at': datetime.now().isoformat(),
            'total_count': len(self.emails),
            'urgent_count': self._count_by_category('urgent'),
            'normal_count': self._count_by_category('normal'),
            'low_count': self._count_by_category('low'),
            'emails': self.emails
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 Saved to: {output_path}")
    
    def print_summary(self, max_display: int = 20):
        """Print a human-readable summary"""
        print("\n" + "="*80)
        print("📬 UNIFIED EMAIL TRIAGE QUEUE")
        print("="*80 + "\n")
        
        # Show urgent emails first
        urgent = self.get_by_category('urgent')
        if urgent:
            print(f"🚨 URGENT ({len(urgent)} emails):\n")
            for i, email in enumerate(urgent[:max_display], 1):
                self._print_email_summary(i, email)
            if len(urgent) > max_display:
                print(f"   ... and {len(urgent) - max_display} more urgent emails\n")
        
        # Show normal priority
        normal = self.get_by_category('normal')
        if normal:
            print(f"\n📋 NORMAL ({len(normal)} emails):\n")
            for i, email in enumerate(normal[:max_display], 1):
                self._print_email_summary(i, email)
            if len(normal) > max_display:
                print(f"   ... and {len(normal) - max_display} more normal emails\n")
        
        # Just count low priority
        low = self.get_by_category('low')
        if low:
            print(f"\n📉 LOW ({len(low)} emails) - not displayed\n")
        
        print("="*80)
    
    def _print_email_summary(self, index: int, email: Dict[str, Any]):
        """Print a single email summary"""
        score = email.get('priority_score', 0)
        subject = email.get('subject', '(no subject)')[:60]
        from_addr = email.get('from', '')[:40]
        provider = email.get('provider', '').upper()
        unread = "●" if email.get('is_unread') else "○"
        
        print(f"   {index}. [{score:3d}] {unread} {subject}")
        print(f"       From: {from_addr} ({provider})")
        print()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch and aggregate emails from all inboxes')
    parser.add_argument('--mode', choices=['unread', 'recent', 'all'], default='unread',
                        help='Fetch mode (default: unread)')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours to look back (for mode=recent)')
    parser.add_argument('--limit', type=int, default=50,
                        help='Max emails per account (default: 50)')
    parser.add_argument('--output', type=str,
                        help='Save results to JSON file')
    parser.add_argument('--json', action='store_true',
                        help='Output raw JSON instead of summary')
    
    args = parser.parse_args()
    
    # Initialize aggregator
    aggregator = UnifiedEmailAggregator()
    
    # Fetch all emails
    emails = aggregator.fetch_all(
        mode=args.mode,
        hours=args.hours,
        limit_per_account=args.limit
    )
    
    # Output
    if args.json:
        print(json.dumps({
            'total_count': len(emails),
            'emails': emails
        }, indent=2))
    else:
        aggregator.print_summary()
    
    # Save to file if requested
    if args.output:
        aggregator.save_to_json(args.output)


if __name__ == '__main__':
    main()
