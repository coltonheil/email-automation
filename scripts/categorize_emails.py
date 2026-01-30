#!/usr/bin/env python3
"""
Categorize Emails
Auto-categorize all uncategorized emails
"""

import os
import sys
import argparse
import json

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from categorizer import EmailCategorizer


def main():
    parser = argparse.ArgumentParser(description='Auto-categorize emails')
    parser.add_argument('--limit', type=int, default=1000, help='Max emails to process')
    parser.add_argument('--stats', action='store_true', help='Show category stats')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    categorizer = EmailCategorizer()
    
    if args.stats:
        # Just show stats
        stats = categorizer.get_category_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n📊 Category Statistics")
            print("=" * 50)
            
            total = sum(s['count'] for s in stats.values())
            
            for category, data in sorted(stats.items(), key=lambda x: -x[1]['count']):
                pct = (data['count'] / total * 100) if total > 0 else 0
                print(f"\n{category.upper()}")
                print(f"  Count: {data['count']} ({pct:.1f}%)")
                print(f"  Unread: {data['unread']}")
                print(f"  Avg Priority: {data['avg_priority']}/100")
            
            print("\n" + "=" * 50)
            print(f"Total categorized: {total}")
    else:
        # Recategorize
        if not args.json:
            print(f"🏷️  Categorizing up to {args.limit} emails...")
        
        results = categorizer.recategorize_all(limit=args.limit)
        
        if args.json:
            print(json.dumps({
                'success': True,
                'categories': results,
                'total': sum(results.values())
            }, indent=2))
        else:
            print("\n✅ Categorization complete!")
            print("-" * 30)
            for category, count in sorted(results.items(), key=lambda x: -x[1]):
                print(f"  {category}: {count}")
            print("-" * 30)
            print(f"  Total: {sum(results.values())}")


if __name__ == '__main__':
    main()
