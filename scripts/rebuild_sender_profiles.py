#!/usr/bin/env python3
"""
Rebuild Sender Profiles
Regenerate sender_profiles table from email history
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from database import EmailDatabase


def main():
    parser = argparse.ArgumentParser(description='Rebuild sender profiles from email history')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be rebuilt')
    
    args = parser.parse_args()
    
    db = EmailDatabase()
    cursor = db.conn.cursor()
    
    print("\n👥 Rebuilding sender profiles...")
    
    # Get all unique senders
    cursor.execute("""
        SELECT 
            from_email,
            MAX(from_name) as name,
            COUNT(*) as total_emails,
            MAX(received_at) as last_email_at,
            MIN(received_at) as first_email_at,
            ROUND(AVG(priority_score), 1) as avg_priority
        FROM emails
        WHERE from_email IS NOT NULL AND from_email != ''
        GROUP BY from_email
        ORDER BY total_emails DESC
    """)
    
    senders = cursor.fetchall()
    print(f"   Found {len(senders)} unique senders")
    
    if args.dry_run:
        print("\n[DRY RUN] Would rebuild these profiles:")
        for row in senders[:10]:
            print(f"   - {row[0]}: {row[2]} emails, avg priority {row[5]}")
        if len(senders) > 10:
            print(f"   ... and {len(senders) - 10} more")
        return
    
    # Recreate sender_profiles table
    cursor.execute("DROP TABLE IF EXISTS sender_profiles_new")
    cursor.execute("""
        CREATE TABLE sender_profiles_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            total_emails_received INTEGER DEFAULT 0,
            first_email_at TEXT,
            last_email_at TEXT,
            avg_priority_score REAL,
            relationship_type TEXT,
            is_vip INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Insert profiles
    for row in senders:
        email, name, total, last_at, first_at, avg_priority = row
        
        # Determine relationship type
        relationship = 'personal'
        email_lower = email.lower()
        
        if any(x in email_lower for x in ['no-reply', 'noreply', 'notifications']):
            relationship = 'automated'
        elif any(x in email_lower for x in ['newsletter', 'marketing', 'updates']):
            relationship = 'newsletter'
        elif avg_priority and avg_priority >= 70:
            relationship = 'business'
        
        cursor.execute("""
            INSERT INTO sender_profiles_new 
            (email, name, total_emails_received, first_email_at, last_email_at, avg_priority_score, relationship_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email, name, total, first_at, last_at, avg_priority, relationship))
    
    # Swap tables
    cursor.execute("DROP TABLE IF EXISTS sender_profiles_old")
    try:
        cursor.execute("ALTER TABLE sender_profiles RENAME TO sender_profiles_old")
    except:
        pass
    cursor.execute("ALTER TABLE sender_profiles_new RENAME TO sender_profiles")
    cursor.execute("DROP TABLE IF EXISTS sender_profiles_old")
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sender_profiles_email ON sender_profiles(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sender_profiles_relationship ON sender_profiles(relationship_type)")
    
    db.conn.commit()
    
    print(f"\n✅ Rebuilt {len(senders)} sender profiles")
    
    # Show stats
    cursor.execute("SELECT relationship_type, COUNT(*) FROM sender_profiles GROUP BY relationship_type")
    print("\nRelationship breakdown:")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]}")
    
    db.close()


if __name__ == '__main__':
    main()
