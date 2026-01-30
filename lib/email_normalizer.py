#!/usr/bin/env python3
"""
Email Normalizer - Standardizes emails from different providers
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib


class EmailNormalizer:
    """Normalizes emails from Gmail, Outlook, and Instantly into a standard format"""
    
    @staticmethod
    def normalize(email: Dict[str, Any], provider: str, account_id: str) -> Dict[str, Any]:
        """
        Normalize an email from any provider into standard format
        
        Args:
            email: Raw email data from provider
            provider: 'gmail', 'outlook', or 'instantly'
            account_id: Account identifier
            
        Returns:
            Standardized email dict
        """
        if provider == 'gmail':
            return EmailNormalizer._normalize_gmail(email, account_id)
        elif provider == 'outlook':
            return EmailNormalizer._normalize_outlook(email, account_id)
        elif provider == 'instantly':
            return EmailNormalizer._normalize_instantly(email, account_id)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    def _normalize_gmail(email: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Normalize Gmail message from Composio"""
        if not email:
            raise ValueError("Empty email object")
        
        # Composio Gmail uses direct fields (not nested headers)
        msg_id = email.get('messageId') or email.get('id')
        
        # Extract body from messageText or payload
        body = email.get('messageText', '')
        if not body:
            payload = email.get('payload', {})
            body = EmailNormalizer._extract_gmail_body(payload)
        
        # Parse date
        date_str = email.get('messageTimestamp') or email.get('internalDate')
        if date_str:
            try:
                if 'T' in str(date_str):
                    # ISO format
                    received_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # Milliseconds since epoch
                    timestamp = int(date_str) / 1000
                    received_at = datetime.fromtimestamp(timestamp)
            except:
                received_at = datetime.now()
        else:
            received_at = datetime.now()
        
        # Get labels
        labels = email.get('labelIds', [])
        if isinstance(labels, str):
            # Parse string representation of list
            labels = [l.strip().strip("'") for l in labels.strip('[]').split(',') if l.strip()]
        
        # Get preview/snippet
        preview = email.get('preview')
        if preview is None:
            snippet = email.get('snippet', '')
        elif isinstance(preview, dict):
            snippet = preview.get('body', '') or email.get('snippet', '')
        else:
            snippet = str(preview) if preview else ''
        
        return {
            'id': f"gmail_{account_id}_{msg_id}",
            'provider': 'gmail',
            'account_id': account_id,
            'message_id': msg_id,
            'thread_id': email.get('threadId'),
            'subject': email.get('subject', '(no subject)'),
            'from': email.get('sender', ''),
            'to': email.get('to', ''),
            'cc': email.get('cc', ''),
            'bcc': email.get('bcc', ''),
            'body': body,
            'snippet': snippet[:500] if snippet else '',
            'labels': labels,
            'is_unread': 'UNREAD' in labels,
            'is_important': 'IMPORTANT' in labels,
            'received_at': received_at.isoformat() if hasattr(received_at, 'isoformat') else str(received_at),
            'has_attachments': len(email.get('attachmentList', [])) > 0,
            'raw_data': email
        }
    
    @staticmethod
    def _normalize_outlook(email: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Normalize Outlook message from Composio"""
        # Outlook through Microsoft Graph API
        received_at_str = email.get('receivedDateTime', '')
        try:
            received_at = datetime.fromisoformat(received_at_str.replace('Z', '+00:00'))
        except:
            received_at = datetime.now()
        
        # Extract body
        body_data = email.get('body', {})
        body = body_data.get('content', '')
        
        # Parse recipients
        from_addr = email.get('from', {}).get('emailAddress', {})
        to_recipients = email.get('toRecipients', [])
        cc_recipients = email.get('ccRecipients', [])
        
        return {
            'id': f"outlook_{account_id}_{email.get('id')}",
            'provider': 'outlook',
            'account_id': account_id,
            'message_id': email.get('id'),
            'thread_id': email.get('conversationId'),
            'subject': email.get('subject', '(no subject)'),
            'from': f"{from_addr.get('name', '')} <{from_addr.get('address', '')}>",
            'to': ', '.join([f"{r['emailAddress']['name']} <{r['emailAddress']['address']}>" for r in to_recipients]),
            'cc': ', '.join([f"{r['emailAddress']['name']} <{r['emailAddress']['address']}>" for r in cc_recipients]),
            'bcc': '',
            'body': body,
            'snippet': email.get('bodyPreview', ''),
            'labels': [email.get('categories', [])],
            'is_unread': not email.get('isRead', True),
            'is_important': email.get('importance', '') == 'high',
            'received_at': received_at.isoformat(),
            'has_attachments': email.get('hasAttachments', False),
            'raw_data': email
        }
    
    @staticmethod
    def _normalize_instantly(email: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Normalize Instantly message"""
        # Instantly API format (to be confirmed with actual API response)
        received_at_str = email.get('created_at', '')
        try:
            received_at = datetime.fromisoformat(received_at_str)
        except:
            received_at = datetime.now()
        
        return {
            'id': f"instantly_{account_id}_{email.get('id')}",
            'provider': 'instantly',
            'account_id': account_id,
            'message_id': email.get('id'),
            'thread_id': email.get('campaign_id'),
            'subject': email.get('subject', '(no subject)'),
            'from': email.get('from_email', ''),
            'to': email.get('to_email', ''),
            'cc': '',
            'bcc': '',
            'body': email.get('body', ''),
            'snippet': email.get('preview', '')[:200],
            'labels': [email.get('campaign_name', '')],
            'is_unread': email.get('status', '') == 'unread',
            'is_important': False,
            'received_at': received_at.isoformat(),
            'has_attachments': False,
            'raw_data': email
        }
    
    @staticmethod
    def _extract_gmail_body(payload: Dict[str, Any]) -> str:
        """Extract email body from Gmail payload"""
        if not payload:
            return ""
        
        # Check for text/plain part first
        parts = payload.get('parts', [])
        
        if not parts:
            # Single-part message
            body_data = payload.get('body', {}).get('data', '')
            return EmailNormalizer._decode_base64url(body_data)
        
        # Multi-part message - prefer text/plain
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                return EmailNormalizer._decode_base64url(body_data)
        
        # Fallback to HTML or first available part
        for part in parts:
            body_data = part.get('body', {}).get('data', '')
            if body_data:
                return EmailNormalizer._decode_base64url(body_data)
        
        return ""
    
    @staticmethod
    def _decode_base64url(data: str) -> str:
        """Decode base64url-encoded string"""
        import base64
        if not data:
            return ""
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        # Replace URL-safe chars
        data = data.replace('-', '+').replace('_', '/')
        try:
            return base64.b64decode(data).decode('utf-8', errors='ignore')
        except:
            return ""
    
    @staticmethod
    def _has_attachments_gmail(payload: Dict[str, Any]) -> bool:
        """Check if Gmail message has attachments"""
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('filename'):
                return True
        return False
    
    @staticmethod
    def generate_dedup_key(email: Dict[str, Any]) -> str:
        """Generate deduplication key for an email"""
        # Use subject + from + timestamp (rounded to minute) for deduplication
        subject = email.get('subject', '').lower().strip()
        from_addr = email.get('from', '').lower().strip()
        received_at = email.get('received_at', '')
        
        # Round timestamp to minute to catch duplicates within same minute
        try:
            dt = datetime.fromisoformat(received_at)
            rounded = dt.replace(second=0, microsecond=0).isoformat()
        except:
            rounded = received_at
        
        key_string = f"{subject}|{from_addr}|{rounded}"
        return hashlib.md5(key_string.encode()).hexdigest()
