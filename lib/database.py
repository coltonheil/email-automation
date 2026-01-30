#!/usr/bin/env python3
"""
Database module for email automation
Handles SQLite operations for persistent storage
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class EmailDatabase:
    """Manages email storage in SQLite"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to database/emails.db in project root
            project_root = Path(__file__).parent.parent
            db_path = project_root / 'database' / 'emails.db'
        
        self.db_path = str(db_path)
        self.conn = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists and is initialized"""
        # Create database directory if needed
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connect to database (creates if doesn't exist)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        
        # Load and execute schema
        schema_path = Path(__file__).parent.parent / 'database' / 'schema.sql'
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                self.conn.executescript(schema_sql)
                self.conn.commit()
    
    def store_email(self, email: Dict[str, Any]) -> str:
        """
        Store or update an email in database
        
        Args:
            email: Normalized email dict
            
        Returns:
            Email ID
        """
        cursor = self.conn.cursor()
        
        # Extract fields
        email_id = email.get('id')
        provider = email.get('provider')
        account_id = email.get('account_id')
        message_id = email.get('message_id')
        thread_id = email.get('thread_id')
        subject = email.get('subject', '')
        
        # Parse from email (extract address and name)
        from_full = email.get('from', '')
        from_email = self._extract_email_address(from_full)
        from_name = self._extract_name(from_full)
        
        to_email = email.get('to', '')
        cc = email.get('cc', '')
        bcc = email.get('bcc', '')
        body = email.get('body', '')
        snippet = email.get('snippet', '')
        labels = json.dumps(email.get('labels', []))
        is_unread = 1 if email.get('is_unread', True) else 0
        is_important = 1 if email.get('is_important', False) else 0
        has_attachments = 1 if email.get('has_attachments', False) else 0
        received_at = email.get('received_at')
        priority_score = email.get('priority_score', 50)
        priority_category = email.get('priority_category', 'normal')
        raw_data = json.dumps(email.get('raw_data', {}))
        
        # Insert or replace (upsert)
        cursor.execute("""
            INSERT OR REPLACE INTO emails (
                id, provider, account_id, message_id, thread_id,
                subject, from_email, from_name, to_email, cc, bcc,
                body, snippet, labels, is_unread, is_important, has_attachments,
                received_at, priority_score, priority_category, raw_data,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            email_id, provider, account_id, message_id, thread_id,
            subject, from_email, from_name, to_email, cc, bcc,
            body, snippet, labels, is_unread, is_important, has_attachments,
            received_at, priority_score, priority_category, raw_data
        ))
        
        self.conn.commit()
        
        # Update sender profile
        self._update_sender_profile(from_email, from_name, email)
        
        return email_id
    
    def store_emails_batch(self, emails: List[Dict[str, Any]]) -> int:
        """
        Store multiple emails in a batch (more efficient)
        
        Args:
            emails: List of normalized email dicts
            
        Returns:
            Number of emails stored
        """
        count = 0
        for email in emails:
            self.store_email(email)
            count += 1
        return count
    
    def get_unread_emails(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unread emails from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM emails
            WHERE is_unread = 1
            ORDER BY priority_score DESC, received_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_urgent_unread_emails(self) -> List[Dict[str, Any]]:
        """Get urgent unread emails (priority >= 80)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM unread_urgent_emails")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_emails_by_filter(self, filter_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get emails by filter
        
        Args:
            filter_type: 'all', 'unread', 'urgent', 'normal', 'low'
            limit: Max number of emails to return
        """
        cursor = self.conn.cursor()
        
        if filter_type == 'all':
            cursor.execute("""
                SELECT * FROM emails
                ORDER BY received_at DESC
                LIMIT ?
            """, (limit,))
        elif filter_type == 'unread':
            cursor.execute("""
                SELECT * FROM emails
                WHERE is_unread = 1
                ORDER BY priority_score DESC, received_at DESC
                LIMIT ?
            """, (limit,))
        elif filter_type == 'urgent':
            cursor.execute("""
                SELECT * FROM emails
                WHERE priority_category = 'urgent'
                ORDER BY received_at DESC
                LIMIT ?
            """, (limit,))
        elif filter_type == 'normal':
            cursor.execute("""
                SELECT * FROM emails
                WHERE priority_category = 'normal'
                ORDER BY received_at DESC
                LIMIT ?
            """, (limit,))
        elif filter_type == 'low':
            cursor.execute("""
                SELECT * FROM emails
                WHERE priority_category = 'low'
                ORDER BY received_at DESC
                LIMIT ?
            """, (limit,))
        else:
            return []
        
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_as_read(self, email_id: str):
        """Mark email as read"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE emails
            SET is_unread = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (email_id,))
        self.conn.commit()
    
    def _update_sender_profile(self, email_address: str, name: str, email: Dict[str, Any]):
        """Update or create sender profile"""
        if not email_address:
            return
        
        cursor = self.conn.cursor()
        
        # Check if profile exists
        cursor.execute("""
            SELECT id, total_emails_received FROM sender_profiles
            WHERE email_address = ?
        """, (email_address,))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing profile
            profile_id = row['id']
            total_emails = row['total_emails_received'] + 1
            
            cursor.execute("""
                UPDATE sender_profiles
                SET total_emails_received = ?,
                    last_email_at = ?,
                    name = COALESCE(?, name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (total_emails, email.get('received_at'), name, profile_id))
        else:
            # Create new profile
            cursor.execute("""
                INSERT INTO sender_profiles (
                    email_address, name, total_emails_received, last_email_at
                ) VALUES (?, ?, 1, ?)
            """, (email_address, name, email.get('received_at')))
        
        self.conn.commit()
    
    def get_sender_profile(self, email_address: str) -> Optional[Dict[str, Any]]:
        """Get sender profile by email address"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sender_profiles
            WHERE email_address = ?
        """, (email_address,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_sender_email_history(self, email_address: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get past emails from a specific sender"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM emails
            WHERE from_email = ?
            ORDER BY received_at DESC
            LIMIT ?
        """, (email_address, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def log_sync(self, account_id: str, emails_fetched: int, new_emails: int, status: str = 'completed', error: str = None):
        """Log a sync operation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log (
                account_id, sync_completed_at, emails_fetched, new_emails, status, error_message
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """, (account_id, emails_fetched, new_emails, status, error))
        self.conn.commit()
    
    def get_last_sync(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get last successful sync for an account"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_log
            WHERE account_id = ? AND status = 'completed'
            ORDER BY sync_completed_at DESC
            LIMIT 1
        """, (account_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def cleanup_old_read_emails(self, days: int = 30):
        """Delete read emails older than N days"""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM emails
            WHERE is_unread = 0
              AND datetime(received_at) < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted
    
    @staticmethod
    def _extract_email_address(from_field: str) -> str:
        """Extract email address from 'Name <email@example.com>' format"""
        import re
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1).strip()
        return from_field.strip()
    
    @staticmethod
    def _extract_name(from_field: str) -> str:
        """Extract name from 'Name <email@example.com>' format"""
        if '<' in from_field:
            return from_field.split('<')[0].strip().strip('"')
        return ''
    
    # Draft Approval Workflow Methods
    
    def approve_draft(
        self,
        draft_id: int,
        approved_by: str = "user",
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark draft as approved
        
        Args:
            draft_id: Draft ID
            approved_by: Who approved it
            notes: Optional approval notes
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Update draft
        cursor.execute("""
            UPDATE draft_responses
            SET approved_at = ?, approved_by = ?, status = 'approved'
            WHERE id = ?
        """, (now, approved_by, draft_id))
        
        # Log to history
        cursor.execute("""
            INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes)
            VALUES (?, 'approved', ?, ?, ?)
        """, (draft_id, approved_by, now, notes))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def reject_draft(
        self,
        draft_id: int,
        rejected_by: str = "user",
        reason: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark draft as rejected
        
        Args:
            draft_id: Draft ID
            rejected_by: Who rejected it
            reason: Rejection reason
            notes: Optional rejection notes
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Update draft
        cursor.execute("""
            UPDATE draft_responses
            SET rejected_at = ?, rejected_by = ?, rejection_reason = ?, status = 'rejected'
            WHERE id = ?
        """, (now, rejected_by, reason, draft_id))
        
        # Log to history
        cursor.execute("""
            INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes)
            VALUES (?, 'rejected', ?, ?, ?)
        """, (draft_id, rejected_by, now, notes or reason))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def edit_draft(
        self,
        draft_id: int,
        edited_text: str,
        edited_by: str = "user",
        notes: Optional[str] = None
    ) -> bool:
        """
        Record user's edited version of draft
        
        Args:
            draft_id: Draft ID
            edited_text: User's edited text
            edited_by: Who edited it
            notes: Optional edit notes
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Update draft
        cursor.execute("""
            UPDATE draft_responses
            SET edited_text = ?
            WHERE id = ?
        """, (edited_text, draft_id))
        
        # Log to history
        metadata = json.dumps({
            'edited_length': len(edited_text),
            'original_length': self._get_draft_length(draft_id)
        })
        
        cursor.execute("""
            INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
            VALUES (?, 'edited', ?, ?, ?, ?)
        """, (draft_id, edited_by, now, notes, metadata))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def mark_draft_sent(
        self,
        draft_id: int,
        sent_via: str = "manual",
        sent_by: str = "user",
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark draft as sent
        
        Args:
            draft_id: Draft ID
            sent_via: How it was sent (manual, gmail_ui, etc.)
            sent_by: Who sent it
            notes: Optional notes
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Update draft
        cursor.execute("""
            UPDATE draft_responses
            SET sent_at = ?, sent_via = ?, status = 'sent'
            WHERE id = ?
        """, (now, sent_via, draft_id))
        
        # Log to history
        cursor.execute("""
            INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
            VALUES (?, 'sent', ?, ?, ?, ?)
        """, (draft_id, sent_by, now, notes, json.dumps({'via': sent_via})))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def rate_draft(
        self,
        draft_id: int,
        score: int,
        feedback_notes: Optional[str] = None,
        rated_by: str = "user"
    ) -> bool:
        """
        Rate draft quality (1-5)
        
        Args:
            draft_id: Draft ID
            score: Rating score (1-5)
            feedback_notes: Optional feedback
            rated_by: Who rated it
            
        Returns:
            True if successful
        """
        if not 1 <= score <= 5:
            raise ValueError("Score must be between 1 and 5")
        
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # Update draft
        cursor.execute("""
            UPDATE draft_responses
            SET feedback_score = ?, feedback_notes = ?
            WHERE id = ?
        """, (score, feedback_notes, draft_id))
        
        # Log to history
        cursor.execute("""
            INSERT INTO draft_approval_history (draft_id, action, performed_by, performed_at, notes, metadata)
            VALUES (?, 'rated', ?, ?, ?, ?)
        """, (draft_id, rated_by, now, feedback_notes, json.dumps({'score': score})))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_draft_history(self, draft_id: int) -> List[Dict[str, Any]]:
        """
        Get approval history for a draft
        
        Args:
            draft_id: Draft ID
            
        Returns:
            List of history entries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM draft_approval_history
            WHERE draft_id = ?
            ORDER BY performed_at DESC
        """, (draft_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_draft_length(self, draft_id: int) -> int:
        """Get length of original draft text"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT draft_text FROM draft_responses WHERE id = ?", (draft_id,))
        row = cursor.fetchone()
        return len(row['draft_text']) if row else 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
