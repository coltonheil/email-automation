#!/usr/bin/env python3
"""
Sender Context Analyzer
Builds intelligent profiles from email history for contextual draft generation
"""

import re
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime, timedelta
try:
    from text_utils import clean_email_body, summarize_email_for_context
except ImportError:
    from .text_utils import clean_email_body, summarize_email_for_context


class SenderAnalyzer:
    """Analyzes sender email history to build context for drafting"""
    
    def __init__(self, db):
        """
        Initialize analyzer
        
        Args:
            db: EmailDatabase instance
        """
        self.db = db
    
    def build_sender_context(self, sender_email: str, current_email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive sender context for draft generation
        
        Args:
            sender_email: Email address of sender
            current_email: The current email needing a response
            
        Returns:
            Context dict with sender profile, history, topics, patterns
        """
        # Get sender profile
        profile = self.db.get_sender_profile(sender_email)
        
        # CRITICAL: Limit history to 10 emails to prevent context overflow
        history = self.db.get_sender_email_history(sender_email, limit=10)
        
        # Analyze history (use clean_history for topics, but original for other analysis)
        relationship_type = self._determine_relationship_type(sender_email, history)
        common_topics = self._extract_common_topics(clean_history)  # Use clean version
        response_pattern = self._analyze_response_pattern(clean_history)
        avg_response_time = self._calculate_avg_response_time(clean_history)
        writing_style = self._analyze_writing_style([])  # Skip style analysis to save context
        urgency_level = self._determine_urgency_level(current_email, clean_history)
        
        # CRITICAL: Clean current_email body to prevent context overflow
        # Email bodies can be 500KB+ HTML - must truncate aggressively
        clean_current_email = summarize_email_for_context(current_email, max_body_chars=1500)
        
        # CRITICAL: Strip email bodies from history - only keep metadata
        # This prevents huge context when sender has many long emails
        clean_history = []
        for hist_email in history[:10]:  # Extra safety: limit to 10
            clean_history.append({
                'subject': hist_email.get('subject', ''),
                'snippet': hist_email.get('snippet', '')[:200] if hist_email.get('snippet') else '',
                'received_at': hist_email.get('received_at', ''),
                'priority_score': hist_email.get('priority_score', 50),
                # REMOVED: body, raw_data - only metadata for context
            })
        
        # Build context
        context = {
            'sender_email': sender_email,
            'sender_name': profile.get('name', '') if profile else '',
            'relationship_type': relationship_type,
            'total_emails_received': profile.get('total_emails_received', 0) if profile else 0,
            'last_contact': profile.get('last_email_at', '') if profile else '',
            'avg_priority_score': profile.get('avg_priority_score', 50) if profile else 50,
            'common_topics': common_topics,
            'response_pattern': response_pattern,
            'avg_response_time_hours': avg_response_time,
            'writing_style': writing_style,
            'urgency_level': urgency_level,
            'recent_email_count': len(history),
            'current_email': clean_current_email,  # Use cleaned version
        }
        
        return context
    
    def _determine_relationship_type(self, sender_email: str, history: List[Dict]) -> str:
        """
        Determine relationship type based on email patterns
        
        Returns: 'business', 'personal', 'vendor', 'automated', 'unknown'
        """
        # Check for automated/newsletter patterns
        automated_indicators = [
            'no-reply', 'noreply', 'donotreply', 'notifications',
            'marketing', 'newsletter', 'updates', 'alerts'
        ]
        
        email_lower = sender_email.lower()
        for indicator in automated_indicators:
            if indicator in email_lower:
                return 'automated'
        
        # Check domain for vendors/services
        vendor_domains = [
            'stripe.com', 'paypal.com', 'aws.amazon.com', 'github.com',
            'klaviyo.com', 'sendgrid.net', 'mailchimp.com'
        ]
        
        for domain in vendor_domains:
            if domain in email_lower:
                return 'vendor'
        
        # Analyze email content patterns
        if history:
            subjects = [email.get('subject', '').lower() for email in history]
            combined = ' '.join(subjects)
            
            # Business indicators
            business_keywords = [
                'invoice', 'payment', 'contract', 'proposal', 'meeting',
                'project', 'deadline', 'budget', 'team', 'client'
            ]
            
            business_count = sum(1 for keyword in business_keywords if keyword in combined)
            
            if business_count >= 3:
                return 'business'
        
        # Default to personal if no clear indicators
        return 'personal'
    
    def _extract_common_topics(self, history: List[Dict], top_n: int = 5) -> List[str]:
        """Extract common topics from email subjects"""
        if not history:
            return []
        
        # Collect all subjects
        subjects = [email.get('subject', '') for email in history]
        
        # Extract meaningful words (filter out common words)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
            're', 'fwd', 'fw'
        }
        
        words = []
        for subject in subjects:
            # Extract words (alphanumeric only)
            subject_words = re.findall(r'\b[a-zA-Z]{3,}\b', subject.lower())
            words.extend([w for w in subject_words if w not in stopwords])
        
        # Count frequencies
        word_counts = Counter(words)
        
        # Return top N topics
        return [word for word, count in word_counts.most_common(top_n)]
    
    def _analyze_response_pattern(self, history: List[Dict]) -> str:
        """
        Analyze how often this sender is responded to
        
        Returns: 'always_respond', 'sometimes_respond', 'rarely_respond', 'unknown'
        """
        if len(history) < 3:
            return 'unknown'
        
        # For now, return 'sometimes_respond' as we don't track sent emails yet
        # In future: query sent emails to determine actual response pattern
        return 'sometimes_respond'
    
    def _calculate_avg_response_time(self, history: List[Dict]) -> Optional[int]:
        """
        Calculate average response time in hours
        
        Returns: Average hours or None if insufficient data
        """
        # For now, return None as we don't track sent emails yet
        # In future: calculate time between received and sent emails
        return None
    
    def _analyze_writing_style(self, history: List[Dict]) -> str:
        """
        Analyze writing style from email bodies
        
        Returns: Style description (e.g., 'formal', 'casual', 'concise')
        """
        if not history:
            return 'professional'
        
        # Sample a few emails with bodies
        bodies = [email.get('body', '') for email in history[:5] if email.get('body')]
        
        if not bodies:
            return 'professional'
        
        combined = ' '.join(bodies)
        
        # Analyze formality
        formal_indicators = ['dear', 'sincerely', 'regards', 'respectfully', 'kindly']
        casual_indicators = ['hey', 'hi there', 'thanks!', 'cheers', ':)']
        
        formal_count = sum(1 for word in formal_indicators if word in combined.lower())
        casual_count = sum(1 for word in casual_indicators if word in combined.lower())
        
        if formal_count > casual_count:
            return 'formal'
        elif casual_count > formal_count:
            return 'casual'
        
        # Check average sentence length for conciseness
        sentences = combined.split('.')
        avg_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        if avg_length < 15:
            return 'concise'
        
        return 'professional'
    
    def _determine_urgency_level(self, current_email: Dict, history: List[Dict]) -> str:
        """
        Determine urgency level based on current email and sender history
        
        Returns: 'critical', 'high', 'normal', 'low'
        """
        priority_score = current_email.get('priority_score', 50)
        
        # Check for urgency keywords
        subject = current_email.get('subject', '').lower()
        body = current_email.get('body', '').lower()
        combined = f"{subject} {body}"
        
        critical_keywords = ['urgent', 'asap', 'critical', 'emergency', 'immediate']
        high_keywords = ['important', 'deadline', 'expiring', 'action required']
        
        critical_count = sum(1 for keyword in critical_keywords if keyword in combined)
        high_count = sum(1 for keyword in high_keywords if keyword in combined)
        
        if priority_score >= 90 or critical_count >= 2:
            return 'critical'
        elif priority_score >= 80 or high_count >= 2:
            return 'high'
        elif priority_score >= 60:
            return 'normal'
        else:
            return 'low'
    
    def generate_context_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate human-readable context summary for LLM prompting
        
        Args:
            context: Context dict from build_sender_context()
            
        Returns:
            Formatted context summary string
        """
        summary_parts = []
        
        # Sender info
        summary_parts.append(f"SENDER: {context['sender_name']} <{context['sender_email']}>")
        summary_parts.append(f"RELATIONSHIP: {context['relationship_type'].replace('_', ' ').title()}")
        
        # History
        if context['total_emails_received'] > 0:
            summary_parts.append(f"TOTAL EMAILS: {context['total_emails_received']}")
            summary_parts.append(f"LAST CONTACT: {context['last_contact']}")
        
        # Topics
        if context['common_topics']:
            topics_str = ', '.join(context['common_topics'][:5])
            summary_parts.append(f"COMMON TOPICS: {topics_str}")
        
        # Response pattern
        if context['response_pattern'] != 'unknown':
            pattern = context['response_pattern'].replace('_', ' ').title()
            summary_parts.append(f"RESPONSE PATTERN: {pattern}")
        
        # Writing style
        summary_parts.append(f"WRITING STYLE: {context['writing_style'].title()}")
        
        # Urgency
        summary_parts.append(f"URGENCY: {context['urgency_level'].upper()}")
        
        # Current email
        current = context['current_email']
        summary_parts.append(f"\nCURRENT EMAIL:")
        summary_parts.append(f"Subject: {current.get('subject', '(no subject)')}")
        summary_parts.append(f"Priority Score: {current.get('priority_score', 50)}/100")
        
        snippet = current.get('snippet', '') or current.get('body', '')[:200]
        if snippet:
            summary_parts.append(f"Preview: {snippet}...")
        
        return '\n'.join(summary_parts)
