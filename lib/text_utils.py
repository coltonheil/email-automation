#!/usr/bin/env python3
"""
Text Utilities for Email Automation
Handles text cleaning, truncation, and HTML stripping
"""

import re
import html
from typing import Optional


def strip_html(text: str) -> str:
    """
    Remove HTML tags and decode entities
    
    Args:
        text: HTML or plain text
        
    Returns:
        Clean plain text
    """
    if not text:
        return ""
    
    # Remove script and style elements entirely
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Replace common block elements with newlines
    text = re.sub(r'<(br|p|div|li|tr|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n\s*\n+', '\n\n', text)  # Multiple newlines to double
    text = text.strip()
    
    return text


def truncate_text(text: str, max_chars: int = 4000, suffix: str = "\n\n[...truncated...]") -> str:
    """
    Truncate text to max characters, preserving word boundaries
    
    Args:
        text: Text to truncate
        max_chars: Maximum character length
        suffix: Suffix to append if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_chars:
        return text
    
    # Find last space before limit
    cutoff = max_chars - len(suffix)
    last_space = text[:cutoff].rfind(' ')
    
    if last_space > cutoff * 0.5:  # If reasonable space found
        return text[:last_space] + suffix
    else:
        return text[:cutoff] + suffix


def clean_email_body(body: str, max_chars: int = 1500) -> str:
    """
    Clean and truncate email body for context
    
    Args:
        body: Raw email body (may be HTML)
        max_chars: Maximum character length
        
    Returns:
        Clean, truncated plain text
    """
    if not body:
        return ""
    
    # Strip HTML
    text = strip_html(body)
    
    # Remove common email noise
    # - Forwarded message headers
    text = re.sub(r'[-]+\s*Forwarded message\s*[-]+.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
    # - Long URLs
    text = re.sub(r'https?://[^\s]{100,}', '[long-url]', text)
    # - Base64 encoded content
    text = re.sub(r'[A-Za-z0-9+/=]{100,}', '[encoded-content]', text)
    
    # Truncate
    return truncate_text(text, max_chars)


def summarize_email_for_context(email: dict, max_body_chars: int = 1500) -> dict:
    """
    Create a context-safe summary of an email
    
    Args:
        email: Email dict with body, subject, etc.
        max_body_chars: Max chars for body
        
    Returns:
        Email dict with cleaned/truncated body
    """
    if not email:
        return {}
    
    result = email.copy()
    
    # Clean body
    if 'body' in result:
        result['body'] = clean_email_body(result['body'], max_body_chars)
    
    # Use snippet if body is empty after cleaning
    if not result.get('body') and result.get('snippet'):
        result['body'] = truncate_text(result['snippet'], max_body_chars)
    
    return result
