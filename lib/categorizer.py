#!/usr/bin/env python3
"""
Email Categorizer
Automatically categorize emails for better organization
"""

import re
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from retry_utils import logger


class EmailCategorizer:
    """
    Auto-categorizes emails based on content, sender, and patterns
    
    Categories:
    - financial: Invoices, payments, receipts, billing
    - support: Support tickets, help requests
    - partnership: Business partnerships, collaborations
    - newsletter: Newsletters, digests, marketing
    - action_required: Urgent actions, deadlines
    - security: Security alerts, password resets
    - social: Social notifications (likes, comments, follows)
    - shipping: Order confirmations, tracking updates
    - calendar: Meeting invites, calendar updates
    - personal: Personal emails (no business keywords)
    - other: Uncategorized
    """
    
    # Category definitions with keywords and patterns
    CATEGORIES = {
        'financial': {
            'keywords': [
                'invoice', 'payment', 'receipt', 'billing', 'paid', 'charge',
                'subscription', 'renewal', 'refund', 'transaction', 'statement',
                'balance', 'amount due', 'payment received', 'payment failed'
            ],
            'sender_patterns': [
                r'billing@', r'payments@', r'invoice@', r'accounting@',
                r'@stripe\.com', r'@paypal\.com', r'@square\.com', r'@quickbooks\.'
            ],
            'priority_boost': 10
        },
        'support': {
            'keywords': [
                'ticket', 'support', 'help desk', 'case number', 'issue',
                'bug report', 'feature request', 'feedback', 'assistance',
                'problem', 'trouble', 'resolution', 'escalated'
            ],
            'sender_patterns': [
                r'support@', r'help@', r'helpdesk@', r'service@', r'care@',
                r'@zendesk\.', r'@freshdesk\.', r'@intercom\.'
            ],
            'priority_boost': 5
        },
        'partnership': {
            'keywords': [
                'partnership', 'collaboration', 'opportunity', 'proposal',
                'joint venture', 'affiliate', 'sponsor', 'collaborate',
                'business development', 'strategic', 'alliance'
            ],
            'sender_patterns': [
                r'partnerships@', r'bizdev@', r'bd@'
            ],
            'priority_boost': 15
        },
        'newsletter': {
            'keywords': [
                'unsubscribe', 'newsletter', 'digest', 'weekly update',
                'monthly update', 'roundup', 'bulletin', 'subscribe',
                'email preferences', 'opt out', 'mailing list'
            ],
            'sender_patterns': [
                r'newsletter@', r'news@', r'updates@', r'digest@',
                r'@mailchimp\.', r'@substack\.', r'@convertkit\.',
                r'noreply@', r'no-reply@', r'donotreply@'
            ],
            'priority_boost': -20
        },
        'action_required': {
            'keywords': [
                'action required', 'urgent', 'deadline', 'asap', 'immediate',
                'time sensitive', 'expire', 'expiring', 'last chance',
                'final notice', 'respond by', 'due date', 'overdue'
            ],
            'sender_patterns': [],
            'priority_boost': 25
        },
        'security': {
            'keywords': [
                'security alert', 'password', 'verification', 'suspicious',
                'login attempt', 'two-factor', '2fa', 'authentication',
                'account activity', 'unusual activity', 'compromised',
                'reset your password', 'verify your identity'
            ],
            'sender_patterns': [
                r'security@', r'noreply@.*security', r'alerts@'
            ],
            'priority_boost': 20
        },
        'social': {
            'keywords': [
                'liked your', 'commented on', 'mentioned you', 'followed you',
                'new follower', 'tagged you', 'shared your', 'replied to',
                'new connection', 'invitation to connect', 'endorsed'
            ],
            'sender_patterns': [
                r'@linkedin\.', r'@twitter\.', r'@facebook\.', r'@instagram\.',
                r'notifications@', r'notify@'
            ],
            'priority_boost': -15
        },
        'shipping': {
            'keywords': [
                'order confirmation', 'shipped', 'delivery', 'tracking',
                'out for delivery', 'package', 'shipment', 'carrier',
                'estimated arrival', 'order status', 'dispatched'
            ],
            'sender_patterns': [
                r'orders@', r'shipping@', r'@ups\.', r'@fedex\.', r'@usps\.',
                r'@amazon\.com', r'@shopify\.'
            ],
            'priority_boost': 5
        },
        'calendar': {
            'keywords': [
                'meeting', 'calendar', 'invite', 'rsvp', 'scheduled',
                'appointment', 'event', 'reminder', 'agenda',
                'join meeting', 'zoom', 'google meet', 'teams meeting'
            ],
            'sender_patterns': [
                r'calendar@', r'@calendar\.google\.com', r'@calendly\.'
            ],
            'priority_boost': 10
        }
    }
    
    def __init__(self, db_path: str = "database/emails.db"):
        """Initialize categorizer"""
        self.db_path = db_path
    
    def categorize_email(self, email: Dict[str, Any]) -> Tuple[str, int]:
        """
        Categorize a single email
        
        Args:
            email: Email dict
            
        Returns:
            (category, priority_adjustment)
        """
        subject = (email.get('subject', '') or '').lower()
        body = (email.get('body', '') or email.get('snippet', '') or '').lower()
        from_email = (email.get('from_email', '') or email.get('from', '') or '').lower()
        
        combined_text = f"{subject} {body}"
        
        scores: Dict[str, int] = {}
        
        for category, config in self.CATEGORIES.items():
            score = 0
            
            # Check keywords
            for keyword in config['keywords']:
                if keyword.lower() in combined_text:
                    score += 10
                    if keyword.lower() in subject:
                        score += 5  # Bonus for subject match
            
            # Check sender patterns
            for pattern in config['sender_patterns']:
                if re.search(pattern, from_email, re.IGNORECASE):
                    score += 15
            
            if score > 0:
                scores[category] = score
        
        if not scores:
            return 'other', 0
        
        # Get highest scoring category
        best_category = max(scores, key=scores.get)
        priority_adjustment = self.CATEGORIES[best_category]['priority_boost']
        
        return best_category, priority_adjustment
    
    def categorize_and_update(self, email_id: int) -> Optional[str]:
        """
        Categorize email and update database
        
        Args:
            email_id: Email database ID
            
        Returns:
            Category string or None if failed
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get email
            cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            email = cursor.fetchone()
            
            if not email:
                return None
            
            email = dict(email)
            
            # Categorize
            category, priority_adj = self.categorize_email(email)
            
            # Update email
            cursor.execute("""
                UPDATE emails
                SET category = ?,
                    priority_score = MIN(100, MAX(0, priority_score + ?))
                WHERE id = ?
            """, (category, priority_adj, email_id))
            
            conn.commit()
            logger.debug(f"Categorized email {email_id} as '{category}' (priority adj: {priority_adj})")
            
            return category
            
        except Exception as e:
            logger.error(f"Error categorizing email {email_id}: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def recategorize_all(self, limit: int = 1000) -> Dict[str, int]:
        """
        Recategorize all emails (or up to limit)
        
        Args:
            limit: Maximum emails to process
            
        Returns:
            Dict of category counts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM emails
            WHERE category IS NULL OR category = ''
            ORDER BY received_at DESC
            LIMIT ?
        """, (limit,))
        
        emails = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"Recategorizing {len(emails)} emails")
        
        category_counts: Dict[str, int] = {}
        
        for email in emails:
            category = self.categorize_and_update(email['id'])
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        logger.info(f"Categorization complete: {category_counts}")
        
        return category_counts
    
    def get_category_stats(self) -> Dict[str, Any]:
        """
        Get statistics by category
        
        Returns:
            Dict with counts and averages per category
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                category,
                COUNT(*) as count,
                SUM(CASE WHEN is_unread = 1 THEN 1 ELSE 0 END) as unread,
                ROUND(AVG(priority_score), 1) as avg_priority
            FROM emails
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY count DESC
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                'count': row[1],
                'unread': row[2],
                'avg_priority': row[3]
            }
        
        conn.close()
        return stats
