#!/usr/bin/env python3
"""
Thread Analyzer
Groups emails into conversation threads for better context
"""

import re
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from retry_utils import logger


class ThreadAnalyzer:
    """
    Analyzes and groups emails into conversation threads
    
    Features:
    - Extract thread IDs from email headers
    - Group emails by thread
    - Track thread participants
    - Calculate thread statistics
    """
    
    def __init__(self, db_path: str = "database/emails.db"):
        """
        Initialize thread analyzer
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    def extract_thread_id(self, email: Dict[str, Any]) -> Optional[str]:
        """
        Extract or generate thread ID from email
        
        Args:
            email: Email dict with headers
            
        Returns:
            Thread ID string
        """
        # Check for existing thread ID (from Gmail/Outlook)
        thread_id = email.get('thread_id')
        if thread_id:
            return thread_id
        
        # Try to extract from headers
        raw_data = email.get('raw_data', {})
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except:
                raw_data = {}
        
        # Look for In-Reply-To or References header
        headers = raw_data.get('headers', {})
        in_reply_to = headers.get('In-Reply-To', headers.get('in-reply-to'))
        references = headers.get('References', headers.get('references'))
        
        if in_reply_to:
            # Use the message ID we're replying to
            return self._normalize_message_id(in_reply_to)
        
        if references:
            # Use the first reference (original message)
            refs = references.split()
            if refs:
                return self._normalize_message_id(refs[0])
        
        # Fall back to generating from subject
        subject = email.get('subject', '')
        normalized_subject = self._normalize_subject(subject)
        
        if normalized_subject:
            # Generate thread ID from normalized subject + sender domain
            from_email = email.get('from_email', email.get('from', ''))
            domain = self._extract_domain(from_email)
            return f"subj:{normalized_subject}:{domain}"
        
        # Last resort: use message ID as thread ID
        message_id = email.get('message_id', email.get('id'))
        return message_id
    
    def _normalize_message_id(self, message_id: str) -> str:
        """Normalize a message ID (strip angle brackets, whitespace)"""
        return message_id.strip().strip('<>').strip()
    
    def _normalize_subject(self, subject: str) -> str:
        """
        Normalize subject for thread matching
        
        Removes:
        - Re:, Fwd:, FW:, etc.
        - Extra whitespace
        - Common prefixes
        """
        if not subject:
            return ''
        
        # Remove common prefixes
        patterns = [
            r'^(re|fwd|fw|aw|sv|vs|antw|r|odp|回复|答复|转发):\s*',
            r'^\[.*?\]\s*',  # [External], [SPAM], etc.
        ]
        
        result = subject.lower().strip()
        
        for pattern in patterns:
            while True:
                new_result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
                if new_result == result:
                    break
                result = new_result
        
        # Remove extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result[:100]  # Limit length
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if not email or '@' not in email:
            return 'unknown'
        return email.split('@')[1].lower().strip('>')
    
    def update_thread(self, email: Dict[str, Any]) -> Optional[int]:
        """
        Add email to thread or create new thread
        
        Args:
            email: Email dict
            
        Returns:
            Thread database ID
        """
        thread_id = self.extract_thread_id(email)
        if not thread_id:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if thread exists
            cursor.execute("SELECT id, email_count, max_priority FROM email_threads WHERE thread_id = ?", (thread_id,))
            existing = cursor.fetchone()
            
            email_received_at = email.get('received_at', datetime.now().isoformat())
            priority_score = email.get('priority_score', 50)
            is_unread = 1 if email.get('is_unread', True) else 0
            subject = email.get('subject', '')
            
            if existing:
                # Update existing thread
                thread_db_id, email_count, max_priority = existing
                new_max_priority = max(max_priority or 0, priority_score)
                
                cursor.execute("""
                    UPDATE email_threads
                    SET email_count = email_count + 1,
                        last_message_at = MAX(COALESCE(last_message_at, ''), ?),
                        is_unread = MAX(is_unread, ?),
                        max_priority = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (email_received_at, is_unread, new_max_priority, thread_db_id))
            else:
                # Create new thread
                cursor.execute("""
                    INSERT INTO email_threads (
                        thread_id, subject, email_count, first_email_at, 
                        last_message_at, is_unread, max_priority
                    ) VALUES (?, ?, 1, ?, ?, ?, ?)
                """, (thread_id, subject, email_received_at, email_received_at, is_unread, priority_score))
                thread_db_id = cursor.lastrowid
            
            # Update email record with thread ID
            email_id = email.get('id')
            if email_id:
                cursor.execute("UPDATE emails SET thread_id = ? WHERE id = ?", (thread_id, email_id))
            
            # Update participants
            self._update_participants(cursor, thread_id, email)
            
            conn.commit()
            logger.debug(f"Updated thread {thread_id} (DB ID: {thread_db_id})")
            return thread_db_id
            
        except Exception as e:
            logger.error(f"Error updating thread: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _update_participants(self, cursor, thread_id: str, email: Dict[str, Any]):
        """Update thread participants from email"""
        now = datetime.now().isoformat()
        
        participants = []
        
        # Add sender
        from_email = email.get('from_email', '')
        from_name = email.get('from_name', '')
        if from_email:
            participants.append((from_email, from_name, 'sender'))
        
        # Add recipients
        to_email = email.get('to', email.get('to_email', ''))
        if to_email:
            for addr in self._parse_email_list(to_email):
                participants.append((addr, '', 'recipient'))
        
        # Add CC
        cc = email.get('cc', '')
        if cc:
            for addr in self._parse_email_list(cc):
                participants.append((addr, '', 'cc'))
        
        for email_addr, name, role in participants:
            if not email_addr:
                continue
            
            cursor.execute("""
                INSERT INTO thread_participants (thread_id, email, name, role, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id, email) DO UPDATE SET
                    name = COALESCE(excluded.name, name),
                    message_count = message_count + 1,
                    last_seen = excluded.last_seen
            """, (thread_id, email_addr.lower().strip(), name, role, now, now))
    
    def _parse_email_list(self, email_str: str) -> List[str]:
        """Parse comma-separated email list"""
        if not email_str:
            return []
        
        # Handle both "Name <email@example.com>" and plain email formats
        emails = []
        for part in email_str.split(','):
            part = part.strip()
            match = re.search(r'<([^>]+)>', part)
            if match:
                emails.append(match.group(1))
            elif '@' in part:
                emails.append(part)
        
        return emails
    
    def get_thread_emails(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get all emails in a thread
        
        Args:
            thread_id: Thread ID
            
        Returns:
            List of email dicts, ordered by received_at
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM emails
            WHERE thread_id = ?
            ORDER BY received_at ASC
        """, (thread_id,))
        
        emails = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return emails
    
    def get_thread_context(self, email_id: int) -> Dict[str, Any]:
        """
        Get thread context for a specific email
        
        Args:
            email_id: Email database ID
            
        Returns:
            Dict with thread info and related emails
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the email
        cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
        email = cursor.fetchone()
        
        if not email:
            conn.close()
            return {}
        
        email = dict(email)
        thread_id = email.get('thread_id')
        
        if not thread_id:
            conn.close()
            return {
                'email': email,
                'thread': None,
                'emails_in_thread': [email],
                'participants': []
            }
        
        # Get thread info
        cursor.execute("SELECT * FROM email_threads WHERE thread_id = ?", (thread_id,))
        thread = cursor.fetchone()
        
        # Get all emails in thread
        cursor.execute("""
            SELECT * FROM emails
            WHERE thread_id = ?
            ORDER BY received_at ASC
        """, (thread_id,))
        thread_emails = [dict(row) for row in cursor.fetchall()]
        
        # Get participants
        cursor.execute("""
            SELECT * FROM thread_participants
            WHERE thread_id = ?
            ORDER BY message_count DESC
        """, (thread_id,))
        participants = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'email': email,
            'thread': dict(thread) if thread else None,
            'emails_in_thread': thread_emails,
            'participants': participants
        }
    
    def rebuild_threads(self, limit: int = 1000) -> Dict[str, int]:
        """
        Rebuild thread information from existing emails
        
        Args:
            limit: Maximum emails to process
            
        Returns:
            Stats dict with threads_created, emails_processed
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get emails without thread IDs
        cursor.execute("""
            SELECT * FROM emails
            WHERE thread_id IS NULL OR thread_id = ''
            ORDER BY received_at DESC
            LIMIT ?
        """, (limit,))
        
        emails = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"Rebuilding threads for {len(emails)} emails")
        
        threads_created = 0
        for email in emails:
            try:
                thread_db_id = self.update_thread(email)
                if thread_db_id:
                    threads_created += 1
            except Exception as e:
                logger.error(f"Error processing email {email.get('id')}: {e}")
        
        logger.info(f"Thread rebuild complete: {threads_created} threads created/updated")
        
        return {
            'emails_processed': len(emails),
            'threads_created': threads_created
        }
