#!/usr/bin/env python3
"""
Priority Scorer - Assigns 0-100 priority scores to emails
"""

from typing import Dict, Any, List
import re
from datetime import datetime, timedelta


class PriorityScorer:
    """Calculates priority scores (0-100) for emails"""
    
    # VIP senders (high priority)
    VIP_DOMAINS = [
        'stripe.com',
        'anthropic.com',
        'openai.com',
        'clawdbot.com'
    ]
    
    VIP_KEYWORDS = [
        'urgent',
        'asap',
        'important',
        'critical',
        'action required',
        'deadline',
        'expiring',
        'payment',
        'invoice',
        'security alert',
        'password reset'
    ]
    
    SPAM_INDICATORS = [
        'unsubscribe',
        'no-reply',
        'noreply',
        'newsletter',
        'marketing',
        'promotional'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize priority scorer
        
        Args:
            config: Optional configuration for custom rules
        """
        self.config = config or {}
        self.vip_senders = self.config.get('vip_senders', [])
        self.vip_keywords = self.config.get('vip_keywords', self.VIP_KEYWORDS)
        self.spam_indicators = self.config.get('spam_indicators', self.SPAM_INDICATORS)
    
    def score(self, email: Dict[str, Any]) -> int:
        """
        Calculate priority score for an email
        
        Args:
            email: Normalized email dict
            
        Returns:
            Priority score (0-100)
        """
        score = 50  # Start at neutral
        
        # Factor 1: VIP sender (+30)
        if self._is_vip_sender(email):
            score += 30
        
        # Factor 2: Important keywords in subject (+20)
        if self._has_urgent_keywords(email):
            score += 20
        
        # Factor 3: Marked as important by provider (+15)
        if email.get('is_important', False):
            score += 15
        
        # Factor 4: Unread (+10)
        if email.get('is_unread', True):
            score += 10
        
        # Factor 5: Has attachments (+5)
        if email.get('has_attachments', False):
            score += 5
        
        # Factor 6: Recency (+0 to +15)
        recency_boost = self._calculate_recency_boost(email)
        score += recency_boost
        
        # Factor 7: Thread length (replies indicate importance) (+0 to +10)
        # (To be implemented when we have thread history)
        
        # Penalties
        
        # Penalty 1: Spam indicators (-30)
        if self._is_likely_spam(email):
            score -= 30
        
        # Penalty 2: Older than 7 days (-20)
        if self._is_old(email, days=7):
            score -= 20
        
        # Penalty 3: Newsletter/marketing (-15)
        if self._is_newsletter(email):
            score -= 15
        
        # Clamp score to 0-100
        return max(0, min(100, score))
    
    def _is_vip_sender(self, email: Dict[str, Any]) -> bool:
        """Check if sender is a VIP"""
        from_addr = email.get('from', '').lower()
        
        # Check custom VIP list
        for vip in self.vip_senders:
            if vip.lower() in from_addr:
                return True
        
        # Check VIP domains
        for domain in self.VIP_DOMAINS:
            if domain.lower() in from_addr:
                return True
        
        return False
    
    def _has_urgent_keywords(self, email: Dict[str, Any]) -> bool:
        """Check if subject contains urgent keywords"""
        subject = email.get('subject', '').lower()
        body_snippet = email.get('snippet', '').lower()
        
        combined_text = f"{subject} {body_snippet}"
        
        for keyword in self.vip_keywords:
            if keyword.lower() in combined_text:
                return True
        
        return False
    
    def _is_likely_spam(self, email: Dict[str, Any]) -> bool:
        """Check if email is likely spam"""
        from_addr = email.get('from', '').lower()
        subject = email.get('subject', '').lower()
        
        combined_text = f"{from_addr} {subject}"
        
        spam_count = 0
        for indicator in self.spam_indicators:
            if indicator.lower() in combined_text:
                spam_count += 1
        
        # If 2+ spam indicators, likely spam
        return spam_count >= 2
    
    def _is_newsletter(self, email: Dict[str, Any]) -> bool:
        """Check if email is a newsletter"""
        from_addr = email.get('from', '').lower()
        subject = email.get('subject', '').lower()
        snippet = email.get('snippet', '').lower()
        
        # Common newsletter patterns
        newsletter_patterns = [
            r'newsletter',
            r'digest',
            r'weekly update',
            r'monthly roundup',
            r'unsubscribe',
            r'view in browser'
        ]
        
        combined_text = f"{from_addr} {subject} {snippet}"
        
        for pattern in newsletter_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_recency_boost(self, email: Dict[str, Any]) -> int:
        """Calculate boost based on email recency"""
        received_at_str = email.get('received_at', '')
        
        try:
            received_at = datetime.fromisoformat(received_at_str)
        except:
            return 0
        
        now = datetime.now(received_at.tzinfo) if received_at.tzinfo else datetime.now()
        age = now - received_at
        
        # Last hour: +15
        if age < timedelta(hours=1):
            return 15
        # Last 6 hours: +10
        elif age < timedelta(hours=6):
            return 10
        # Last 24 hours: +5
        elif age < timedelta(days=1):
            return 5
        # Older: 0
        else:
            return 0
    
    def _is_old(self, email: Dict[str, Any], days: int = 7) -> bool:
        """Check if email is older than specified days"""
        received_at_str = email.get('received_at', '')
        
        try:
            received_at = datetime.fromisoformat(received_at_str)
        except:
            return False
        
        now = datetime.now(received_at.tzinfo) if received_at.tzinfo else datetime.now()
        age = now - received_at
        
        return age > timedelta(days=days)
    
    def categorize_priority(self, score: int) -> str:
        """
        Categorize priority score into levels
        
        Args:
            score: Priority score (0-100)
            
        Returns:
            'urgent', 'normal', or 'low'
        """
        if score >= 80:
            return 'urgent'
        elif score >= 40:
            return 'normal'
        else:
            return 'low'
