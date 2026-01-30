#!/usr/bin/env python3
"""
Build VIP List from Sent Emails
Fetches all sent emails from last 6 months and adds recipients to VIP list
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from email_fetcher import EmailFetcher


def main():
    parser = argparse.ArgumentParser(description='Build VIP list from sent emails')
    parser.add_argument('--months', type=int, default=6, help='Look back N months (default: 6)')
    parser.add_argument('--min-emails', type=int, default=1, help='Min emails sent to include (default: 1)')
    parser.add_argument('--dry-run', action='store_true', help='Show VIPs without updating config')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Load account config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'accounts.json')
    with open(config_path) as f:
        accounts = json.load(f)
    
    fetcher = EmailFetcher()
    all_recipients = Counter()
    
    cutoff = datetime.now() - timedelta(days=args.months * 30)
    cutoff_str = cutoff.strftime('%Y/%m/%d')
    
    if not args.json:
        print(f"\n📧 Scanning sent emails from last {args.months} months...")
        print(f"   Cutoff date: {cutoff_str}")
    
    # Fetch from Gmail
    for gmail in accounts.get('gmail', []):
        account_id = gmail['composio_account_id']
        if not args.json:
            print(f"\n   Fetching from Gmail ({gmail['id']})...")
        
        try:
            # Query for sent emails
            emails = fetcher.fetch_gmail(
                account_id=account_id,
                limit=500,
                query=f"in:sent after:{cutoff_str}"
            )
            
            if not args.json:
                print(f"   Found {len(emails)} sent emails")
            
            for email in emails:
                # Extract recipients
                to_field = email.get('to', '') or ''
                cc_field = email.get('cc', '') or ''
                
                for field in [to_field, cc_field]:
                    if not field:
                        continue
                    # Parse email addresses
                    import re
                    addresses = re.findall(r'[\w\.-]+@[\w\.-]+', field)
                    for addr in addresses:
                        addr = addr.lower().strip()
                        if addr and '@' in addr:
                            all_recipients[addr] += 1
        
        except Exception as e:
            if not args.json:
                print(f"   Error: {e}")
    
    # Fetch from Outlook
    for outlook in accounts.get('outlook', []):
        account_id = outlook['composio_account_id']
        if not args.json:
            print(f"\n   Fetching from Outlook ({outlook['id']})...")
        
        try:
            # Outlook sent folder query
            emails = fetcher.fetch_outlook(
                account_id=account_id,
                limit=500,
                filter_query=f"sentDateTime ge {cutoff.isoformat()}Z"
            )
            
            if not args.json:
                print(f"   Found {len(emails)} sent emails")
            
            for email in emails:
                to_field = email.get('toRecipients', [])
                cc_field = email.get('ccRecipients', [])
                
                for recipient_list in [to_field, cc_field]:
                    if isinstance(recipient_list, list):
                        for r in recipient_list:
                            addr = r.get('emailAddress', {}).get('address', '')
                            if addr:
                                all_recipients[addr.lower().strip()] += 1
        
        except Exception as e:
            if not args.json:
                print(f"   Error: {e}")
    
    # Filter by minimum emails
    vip_addresses = [addr for addr, count in all_recipients.items() if count >= args.min_emails]
    
    # Remove obvious non-VIPs
    skip_patterns = ['noreply', 'no-reply', 'donotreply', 'newsletter', 'notifications', 'mailer-daemon']
    vip_addresses = [addr for addr in vip_addresses if not any(p in addr for p in skip_patterns)]
    
    # Sort by frequency
    vip_addresses = sorted(vip_addresses, key=lambda x: all_recipients[x], reverse=True)
    
    if args.json:
        print(json.dumps({
            'total_recipients': len(all_recipients),
            'vip_count': len(vip_addresses),
            'vip_addresses': vip_addresses,
            'top_10': [(addr, all_recipients[addr]) for addr in vip_addresses[:10]]
        }, indent=2))
        return
    
    print(f"\n✅ Found {len(vip_addresses)} unique recipients you've emailed")
    print(f"\nTop 20 most contacted:")
    for addr in vip_addresses[:20]:
        print(f"   {all_recipients[addr]:3d}x  {addr}")
    
    if len(vip_addresses) > 20:
        print(f"   ... and {len(vip_addresses) - 20} more")
    
    if args.dry_run:
        print("\n[DRY RUN] Would add these to VIP list")
        return
    
    # Update sender_filters.json
    filters_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sender_filters.json')
    with open(filters_path) as f:
        filters = json.load(f)
    
    # Add VIP addresses
    existing_vips = set(filters['always_draft'].get('emails', []))
    new_vips = set(vip_addresses)
    
    # Merge and deduplicate
    all_vips = list(existing_vips | new_vips)
    filters['always_draft']['emails'] = sorted(all_vips)
    
    # Save
    with open(filters_path, 'w') as f:
        json.dump(filters, f, indent=2)
    
    print(f"\n✅ Added {len(new_vips - existing_vips)} new VIPs to sender_filters.json")
    print(f"   Total VIPs: {len(all_vips)}")


if __name__ == '__main__':
    main()
