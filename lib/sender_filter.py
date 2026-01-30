#!/usr/bin/env python3
"""
Sender Filter
Whitelist/blacklist logic for draft generation
Prevents wasting API calls on newsletters, no-reply emails, etc.
"""

import json
import os
import re
from typing import Dict, Any, List, Tuple
import sys

# Add lib directory to path
sys.path.insert(0, os.path.dirname(__file__))

from retry_utils import logger


class SenderFilter:
    """
    Filters emails based on sender, domain, relationship type, etc.
    Prevents drafting for newsletters, no-reply, automated emails
    """
    
    def __init__(self, config_path: str = "config/sender_filters.json"):
        """
        Initialize sender filter
        
        Args:
            config_path: Path to sender filters config file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load sender filters config"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded sender filters from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.warning(f"Sender filters config not found: {self.config_path}")
            return self._default_config()
        except Exception as e:
            logger.error(f"Error loading sender filters: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default filter configuration"""
        return {
            "skip_drafting": {
                "emails": ["no-reply@*", "noreply@*"],
                "domains": ["mailchimp.com", "sendgrid.net"],
                "relationship_types": ["automated", "newsletter"]
            },
            "always_draft": {
                "emails": [],
                "domains": [],
                "priority_threshold": 90
            },
            "override": {
                "critical_keywords": ["urgent", "critical", "emergency"]
            }
        }
    
    def should_skip_drafting(
        self,
        sender_email: str,
        sender_context: Dict[str, Any],
        email: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Determine if drafting should be skipped for this email
        
        Args:
            sender_email: Email address of sender
            sender_context: Sender context from SenderAnalyzer
            email: Email dict
            
        Returns:
            (skip, reason) - Tuple of bool and reason string
        """
        # Check for VIP/always-draft first (highest priority)
        if self._is_always_draft(sender_email, email):
            return False, "VIP sender - always draft"
        
        # Check for critical keywords that override filters
        if self._has_critical_keywords(email):
            return False, "Critical keywords detected - override filters"
        
        # Check blacklist patterns
        
        # 1. Check email patterns (no-reply@*, noreply@*)
        if self._matches_email_pattern(sender_email, self.config['skip_drafting']['emails']):
            reason = self._get_skip_reason(sender_email, 'email_pattern')
            logger.info(f"Skipping {sender_email}: {reason}")
            return True, reason
        
        # 2. Check domain blacklist
        if self._matches_domain(sender_email, self.config['skip_drafting']['domains']):
            reason = self._get_skip_reason(sender_email, 'domain')
            logger.info(f"Skipping {sender_email}: {reason}")
            return True, reason
        
        # 3. Check relationship type
        relationship = sender_context.get('relationship_type', 'unknown')
        if relationship in self.config['skip_drafting']['relationship_types']:
            reason = f"Relationship type '{relationship}' is in skip list"
            logger.info(f"Skipping {sender_email}: {reason}")
            return True, reason
        
        # Not filtered
        return False, "OK"
    
    def _is_always_draft(self, sender_email: str, email: Dict[str, Any]) -> bool:
        """Check if sender should always get drafts (VIP)"""
        always_draft = self.config.get('always_draft', {})
        
        # Check email patterns
        if self._matches_email_pattern(sender_email, always_draft.get('emails', [])):
            return True
        
        # Check domains
        if self._matches_domain(sender_email, always_draft.get('domains', [])):
            return True
        
        # Check priority threshold
        priority_threshold = always_draft.get('priority_threshold', 90)
        if email.get('priority_score', 0) >= priority_threshold:
            return True
        
        return False
    
    def _has_critical_keywords(self, email: Dict[str, Any]) -> bool:
        """Check if email contains critical keywords that override filters"""
        override_config = self.config.get('override', {})
        keywords = override_config.get('critical_keywords', [])
        
        if not keywords:
            return False
        
        # Check subject and body
        subject = email.get('subject', '').lower()
        body = email.get('body', email.get('snippet', '')).lower()
        combined = f"{subject} {body}"
        
        for keyword in keywords:
            if keyword.lower() in combined:
                logger.info(f"Critical keyword detected: '{keyword}'")
                return True
        
        return False
    
    def _matches_email_pattern(self, email: str, patterns: List[str]) -> bool:
        """
        Check if email matches any pattern
        
        Supports wildcards:
        - no-reply@* matches no-reply@example.com
        - *@anthropic.com matches any email from anthropic.com
        """
        email_lower = email.lower()
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            
            # Convert wildcard pattern to regex
            regex_pattern = pattern_lower.replace('*', '.*')
            regex_pattern = f"^{regex_pattern}$"
            
            if re.match(regex_pattern, email_lower):
                return True
        
        return False
    
    def _matches_domain(self, email: str, domains: List[str]) -> bool:
        """Check if email domain matches any in list"""
        try:
            email_domain = email.split('@')[1].lower()
            
            for domain in domains:
                if email_domain == domain.lower():
                    return True
        except:
            return False
        
        return False
    
    def _get_skip_reason(self, sender_email: str, filter_type: str) -> str:
        """Get human-readable reason for skipping"""
        reasons = self.config['skip_drafting'].get('reasons', {})
        
        if filter_type == 'email_pattern':
            if 'no-reply' in sender_email.lower() or 'noreply' in sender_email.lower():
                return reasons.get('no-reply', 'No-reply email')
            elif 'newsletter' in sender_email.lower():
                return reasons.get('newsletter', 'Newsletter')
            elif 'marketing' in sender_email.lower():
                return reasons.get('marketing', 'Marketing email')
            else:
                return reasons.get('automated', 'Automated email')
        
        elif filter_type == 'domain':
            return "Blacklisted domain (mail service provider)"
        
        return "Filtered by sender rules"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            "skip_patterns": len(self.config['skip_drafting']['emails']),
            "skip_domains": len(self.config['skip_drafting']['domains']),
            "skip_relationship_types": len(self.config['skip_drafting']['relationship_types']),
            "always_draft_patterns": len(self.config['always_draft']['emails']),
            "always_draft_domains": len(self.config['always_draft']['domains']),
            "critical_keywords": len(self.config['override']['critical_keywords'])
        }
