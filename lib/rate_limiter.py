#!/usr/bin/env python3
"""
Rate Limiter
Prevents API hammering, manages costs, enforces usage limits
"""

import time
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add lib directory to path
sys.path.insert(0, os.path.dirname(__file__))

from retry_utils import logger


class RateLimiter:
    """
    Manages API rate limiting and usage tracking
    
    Features:
    - Max drafts per run
    - Delay between API calls
    - Prevent duplicate drafts (time window)
    - Daily/hourly usage caps
    - Cost tracking
    """
    
    def __init__(
        self,
        db_path: str = "database/emails.db",
        max_drafts_per_run: int = 10,
        min_delay_seconds: float = 2.0,
        duplicate_window_minutes: int = 30,
        max_daily_claude_calls: int = 100,
        max_hourly_claude_calls: int = 20
    ):
        """
        Initialize rate limiter
        
        Args:
            db_path: Path to SQLite database
            max_drafts_per_run: Maximum drafts to generate in single run
            min_delay_seconds: Minimum delay between API calls
            duplicate_window_minutes: Time window to prevent duplicate drafts
            max_daily_claude_calls: Max Claude calls per day
            max_hourly_claude_calls: Max Claude calls per hour
        """
        self.db_path = db_path
        self.max_drafts_per_run = max_drafts_per_run
        self.min_delay_seconds = min_delay_seconds
        self.duplicate_window_minutes = duplicate_window_minutes
        self.max_daily_claude_calls = max_daily_claude_calls
        self.max_hourly_claude_calls = max_hourly_claude_calls
        
        self.drafts_generated_this_run = 0
        self.last_api_call_time = 0
    
    def can_generate_draft(self, email_id: int, sender_email: str) -> tuple[bool, str]:
        """
        Check if we can generate a draft for this email
        
        Args:
            email_id: Email ID
            sender_email: Sender email address
            
        Returns:
            (allowed, reason) - Tuple of bool and reason string
        """
        # Check per-run limit
        if self.drafts_generated_this_run >= self.max_drafts_per_run:
            logger.warning(f"Per-run limit reached ({self.max_drafts_per_run} drafts)")
            return False, f"Per-run limit reached ({self.max_drafts_per_run} drafts)"
        
        # Check daily limit
        daily_calls = self._get_api_calls_count('claude', hours=24)
        if daily_calls >= self.max_daily_claude_calls:
            logger.warning(f"Daily limit reached ({self.max_daily_claude_calls} Claude calls)")
            return False, f"Daily limit reached ({daily_calls}/{self.max_daily_claude_calls} calls)"
        
        # Check hourly limit
        hourly_calls = self._get_api_calls_count('claude', hours=1)
        if hourly_calls >= self.max_hourly_claude_calls:
            logger.warning(f"Hourly limit reached ({self.max_hourly_claude_calls} Claude calls)")
            return False, f"Hourly limit reached ({hourly_calls}/{self.max_hourly_claude_calls} calls)"
        
        # Check for duplicate (recent draft for same sender)
        if self._has_recent_draft(sender_email, self.duplicate_window_minutes):
            logger.info(f"Recent draft exists for {sender_email} (within {self.duplicate_window_minutes}min)")
            return False, f"Draft generated for {sender_email} in last {self.duplicate_window_minutes} minutes"
        
        return True, "OK"
    
    def enforce_delay(self):
        """
        Enforce minimum delay between API calls
        Sleeps if necessary to respect rate limits
        """
        if self.last_api_call_time == 0:
            # First call, no delay needed
            self.last_api_call_time = time.time()
            return
        
        elapsed = time.time() - self.last_api_call_time
        remaining = self.min_delay_seconds - elapsed
        
        if remaining > 0:
            logger.info(f"Rate limit delay: waiting {remaining:.1f}s before next API call")
            time.sleep(remaining)
        
        self.last_api_call_time = time.time()
    
    def record_draft_generated(self, email_id: int, sender_email: str, draft_id: Optional[int] = None):
        """
        Record that a draft was generated
        
        Args:
            email_id: Email ID
            sender_email: Sender email address
            draft_id: Draft ID (if available)
        """
        self.drafts_generated_this_run += 1
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO draft_generation_log (email_id, sender_email, generated_at, draft_id)
            VALUES (?, ?, ?, ?)
        """, (email_id, sender_email, datetime.now().isoformat(), draft_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded draft generation for email {email_id} (run total: {self.drafts_generated_this_run})")
    
    def record_api_usage(
        self,
        service: str,
        action: str,
        success: bool = True,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record API usage for tracking and cost monitoring
        
        Args:
            service: 'composio' or 'claude'
            action: Action name (e.g., 'generate_draft', 'fetch_emails')
            success: Whether the API call succeeded
            tokens_used: Number of tokens used (if available)
            cost_usd: Estimated cost in USD
            metadata: Additional context as dict
        """
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_usage (service, action, timestamp, tokens_used, cost_usd, success, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            service,
            action,
            datetime.now().isoformat(),
            tokens_used,
            cost_usd,
            1 if success else 0,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Recorded {service} API usage: {action} (success={success})")
        
        # Update stats
        self._update_stats(service, success, tokens_used or 0, cost_usd or 0.0)
    
    def _has_recent_draft(self, sender_email: str, window_minutes: int) -> bool:
        """
        Check if a draft was generated for this sender recently
        
        Args:
            sender_email: Sender email address
            window_minutes: Time window in minutes
            
        Returns:
            True if recent draft exists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) FROM draft_generation_log
            WHERE sender_email = ? AND generated_at > ?
        """, (sender_email, cutoff))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def _get_api_calls_count(self, service: str, hours: int) -> int:
        """
        Get number of API calls in the last N hours
        
        Args:
            service: 'composio' or 'claude'
            hours: Number of hours to look back
            
        Returns:
            Number of API calls
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) FROM api_usage
            WHERE service = ? AND timestamp > ? AND success = 1
        """, (service, cutoff))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def _update_stats(self, service: str, success: bool, tokens: int, cost: float):
        """
        Update rate limit statistics
        
        Args:
            service: 'composio' or 'claude'
            success: Whether call succeeded
            tokens: Tokens used
            cost: Cost in USD
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        hour = now.hour
        
        # Upsert stats
        cursor.execute("""
            INSERT INTO rate_limit_stats (date, hour, service, calls_made, calls_blocked, tokens_used, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, hour, service) DO UPDATE SET
                calls_made = calls_made + excluded.calls_made,
                calls_blocked = calls_blocked + excluded.calls_blocked,
                tokens_used = tokens_used + excluded.tokens_used,
                cost_usd = cost_usd + excluded.cost_usd
        """, (
            date_str,
            hour,
            service,
            1 if success else 0,
            0 if success else 1,
            tokens,
            cost
        ))
        
        conn.commit()
        conn.close()
    
    def get_usage_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get usage summary for the last N hours
        
        Args:
            hours: Number of hours to summarize
            
        Returns:
            Dict with usage statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Get counts by service
        cursor.execute("""
            SELECT service, COUNT(*) as calls, SUM(tokens_used) as tokens, SUM(cost_usd) as cost
            FROM api_usage
            WHERE timestamp > ?
            GROUP BY service
        """, (cutoff,))
        
        results = cursor.fetchall()
        conn.close()
        
        summary = {
            "time_window_hours": hours,
            "services": {}
        }
        
        for service, calls, tokens, cost in results:
            summary["services"][service] = {
                "calls": calls,
                "tokens": tokens or 0,
                "cost_usd": cost or 0.0
            }
        
        return summary
    
    def reset_run_counter(self):
        """Reset per-run draft counter (call at start of each run)"""
        self.drafts_generated_this_run = 0
        logger.debug("Reset per-run draft counter")
