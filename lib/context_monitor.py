#!/usr/bin/env python3
"""
Context Size Monitor
Prevents context overflow by monitoring and truncating when needed
"""

import json
from typing import Dict, Any, List


def estimate_token_count(text: str) -> int:
    """
    Rough estimate of token count
    Claude uses ~4 chars per token on average
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def estimate_context_size(sender_context: Dict[str, Any]) -> Dict[str, int]:
    """
    Estimate total context size for draft generation
    
    Args:
        sender_context: Context dict from SenderAnalyzer
        
    Returns:
        Dict with char_count and token_estimate
    """
    # Convert to JSON to get accurate size
    context_json = json.dumps(sender_context, default=str)
    char_count = len(context_json)
    token_estimate = estimate_token_count(context_json)
    
    return {
        'char_count': char_count,
        'token_estimate': token_estimate,
        'safe': token_estimate < 25000  # Claude Opus 4 can handle 200K, but stay safe
    }


def progressive_truncate(sender_context: Dict[str, Any], max_tokens: int = 25000) -> Dict[str, Any]:
    """
    Progressively truncate context if it's too large
    
    Args:
        sender_context: Original context
        max_tokens: Maximum allowed tokens
        
    Returns:
        Truncated context that fits within limit
    """
    # Check current size
    size = estimate_context_size(sender_context)
    
    if size['safe']:
        return sender_context
    
    # Level 1: Truncate email body further
    if 'current_email' in sender_context and sender_context['current_email'].get('body'):
        original_body = sender_context['current_email']['body']
        sender_context['current_email']['body'] = original_body[:1000] + "\n\n[...truncated for context size...]"
    
    size = estimate_context_size(sender_context)
    if size['safe']:
        return sender_context
    
    # Level 2: Remove common_topics
    if 'common_topics' in sender_context:
        sender_context['common_topics'] = sender_context['common_topics'][:3]
    
    size = estimate_context_size(sender_context)
    if size['safe']:
        return sender_context
    
    # Level 3: Emergency - use only current email subject + snippet
    if 'current_email' in sender_context:
        current = sender_context['current_email']
        sender_context['current_email'] = {
            'subject': current.get('subject', ''),
            'snippet': current.get('snippet', '')[:300],
            'from_email': current.get('from_email', ''),
            'priority_score': current.get('priority_score', 50)
        }
    
    return sender_context


def log_context_stats(sender_context: Dict[str, Any], logger) -> None:
    """
    Log context size statistics for debugging
    
    Args:
        sender_context: Context to analyze
        logger: Logger instance
    """
    stats = estimate_context_size(sender_context)
    
    logger.info(f"Context stats: {stats['char_count']:,} chars, ~{stats['token_estimate']:,} tokens")
    
    if not stats['safe']:
        logger.warning(f"Context size approaching limit! Consider truncating.")
