#!/usr/bin/env python3
"""
Email Fetcher - Pulls emails from all connected accounts
With robust error handling and retry logic
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from retry_utils import retry_with_backoff, safe_api_call, logger


class EmailFetcher:
    """Fetches emails from Gmail, Outlook, and Instantly via Composio"""
    
    def __init__(self, composio_api_key: Optional[str] = None):
        """
        Initialize email fetcher
        
        Args:
            composio_api_key: Composio API key (or uses COMPOSIO_API_KEY env var)
        """
        self.api_key = composio_api_key or os.getenv('COMPOSIO_API_KEY')
        if not self.api_key:
            raise ValueError("COMPOSIO_API_KEY not provided")
        
        self.base_url = "https://backend.composio.dev/api/v2"
    
    def fetch_gmail(self, account_id: str, limit: int = 50, query: str = None) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail account
        
        Args:
            account_id: Composio connected account ID
            limit: Maximum number of emails to fetch
            query: Gmail search query (optional)
            
        Returns:
            List of email dicts
        """
        action_name = "GMAIL_FETCH_EMAILS"
        
        input_params = {
            "max_results": limit,
            "verbose": True,
            "include_payload": True
        }
        
        if query:
            input_params["query"] = query
        
        result = self._execute_action(action_name, account_id, input_params)
        
        # Extract messages from response
        if result and 'data' in result:
            data = result['data']
            # Composio wraps response in 'response_data'
            if 'response_data' in data:
                data = data['response_data']
            messages = data.get('messages', [])
            return messages
        
        return []
    
    def fetch_outlook(self, account_id: str, limit: int = 50, filter_query: str = None) -> List[Dict[str, Any]]:
        """
        Fetch emails from Outlook account
        
        Args:
            account_id: Composio connected account ID
            limit: Maximum number of emails to fetch
            filter_query: OData filter query (optional)
            
        Returns:
            List of email dicts
        """
        action_name = "OUTLOOK_OUTLOOK_LIST_MESSAGES"
        
        input_params = {
            "max_results": limit
        }
        
        if filter_query:
            input_params["filter"] = filter_query
        
        result = self._execute_action(action_name, account_id, input_params)
        
        # Extract messages from response
        if result and 'data' in result:
            data = result['data']
            
            # Composio wraps response in 'response_data'
            if 'response_data' in data:
                data = data['response_data']
            
            # Try different possible response structures
            if isinstance(data, list):
                return data
            elif 'value' in data:
                return data['value']
            elif 'messages' in data:
                return data['messages']
        
        return []
    
    def fetch_instantly(self, account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch emails from Instantly workspace
        
        Args:
            account_id: Composio connected account ID
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email dicts
        """
        # Instantly integration - need to check available actions
        # This is a placeholder until we verify the exact Composio action names
        
        action_name = "INSTANTLY_LIST_EMAILS"
        
        input_params = {
            "limit": limit
        }
        
        try:
            result = self._execute_action(action_name, account_id, input_params)
            
            if result and 'data' in result:
                data = result['data']
                # Composio wraps response in 'response_data'
                if 'response_data' in data:
                    data = data['response_data']
                return data.get('emails', [])
        except Exception as e:
            # If action doesn't exist, try alternative approach
            print(f"Warning: Instantly fetch failed: {e}")
            return []
        
        return []
    
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=2.0,
        exceptions=(urllib.error.URLError, urllib.error.HTTPError, ConnectionError, TimeoutError)
    )
    def _execute_action(self, action_name: str, account_id: str, input_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a Composio action with automatic retry on failure
        
        Args:
            action_name: Name of the action (e.g., "GMAIL_LIST_EMAILS")
            account_id: Connected account ID
            input_params: Input parameters for the action
            
        Returns:
            Action result or None on error
            
        Raises:
            Exception: On permanent failure after all retries
        """
        url = f"{self.base_url}/actions/{action_name}/execute"
        
        payload = {
            "connectedAccountId": account_id,
            "input": input_params
        }
        
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        logger.info(f"Executing Composio action: {action_name} (account: {account_id[:8]}...)")
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if not result.get('successful', False):
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"Composio action {action_name} failed: {error_msg}")
                    raise Exception(f"Action failed: {error_msg}")
                
                logger.info(f"Composio action {action_name} succeeded")
                return result
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"HTTP error {e.code} for {action_name}: {error_body}")
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            logger.error(f"Network error for {action_name}: {e.reason}")
            raise Exception(f"Network error: {e.reason}")
        except Exception as e:
            logger.error(f"Action {action_name} execution failed: {str(e)}")
            raise Exception(f"Action execution failed: {str(e)}")
    
    def fetch_unread_only(self, provider: str, account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch only unread emails
        
        Args:
            provider: 'gmail', 'outlook', or 'instantly'
            account_id: Connected account ID
            limit: Maximum number of emails
            
        Returns:
            List of unread emails
        """
        if provider == 'gmail':
            return self.fetch_gmail(account_id, limit=limit, query="is:unread")
        elif provider == 'outlook':
            return self.fetch_outlook(account_id, limit=limit, filter_query="isRead eq false")
        elif provider == 'instantly':
            # Instantly might not support unread filter
            all_emails = self.fetch_instantly(account_id, limit=limit)
            return [e for e in all_emails if e.get('status') == 'unread']
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def fetch_recent(self, provider: str, account_id: str, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch emails from the last N hours
        
        Args:
            provider: 'gmail', 'outlook', or 'instantly'
            account_id: Connected account ID
            hours: Number of hours to look back
            limit: Maximum number of emails
            
        Returns:
            List of recent emails
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        if provider == 'gmail':
            # Gmail date format: after:YYYY/MM/DD
            date_str = cutoff.strftime('%Y/%m/%d')
            query = f"after:{date_str}"
            return self.fetch_gmail(account_id, limit=limit, query=query)
        
        elif provider == 'outlook':
            # Outlook OData filter: receivedDateTime ge YYYY-MM-DDTHH:MM:SSZ
            date_str = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
            filter_query = f"receivedDateTime ge {date_str}"
            return self.fetch_outlook(account_id, limit=limit, filter_query=filter_query)
        
        elif provider == 'instantly':
            # Fetch all and filter client-side
            all_emails = self.fetch_instantly(account_id, limit=limit)
            
            filtered = []
            for email in all_emails:
                created_at = email.get('created_at', '')
                try:
                    email_date = datetime.fromisoformat(created_at)
                    if email_date >= cutoff:
                        filtered.append(email)
                except:
                    continue
            
            return filtered
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
