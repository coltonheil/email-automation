#!/usr/bin/env python3
"""
iMessage Context Builder - Fetches conversation history for context

⛔ SAFETY: This module is READ-ONLY.
   It only reads from the Messages database.
   NO SEND CAPABILITY whatsoever.
   All outputs are for draft generation only.
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL: Import send guard FIRST
from send_guard import SendBlockedError, guard_applescript

# Messages database (READ ONLY)
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")
APPLE_EPOCH = datetime(2001, 1, 1)


@dataclass
class Message:
    """A single message in a conversation."""
    id: int
    guid: str
    text: str
    timestamp: datetime
    is_from_me: bool
    sender: str
    service: str = "iMessage"


@dataclass 
class ConversationContext:
    """Full context for drafting a response."""
    phone: str
    contact_name: Optional[str]
    
    # All recent messages (both directions)
    messages: List[Message] = field(default_factory=list)
    
    # Unread messages needing response
    unread_messages: List[Message] = field(default_factory=list)
    
    # Computed stats
    total_messages: int = 0
    my_message_count: int = 0
    their_message_count: int = 0
    avg_my_message_length: float = 0.0
    avg_their_message_length: float = 0.0
    my_messages_per_turn: float = 1.0  # How many messages I typically send in a row
    
    # Detected patterns
    my_typical_greeting: str = ""
    my_emoji_usage: str = "none"  # none, low, medium, high
    formality_level: str = "casual"  # casual, neutral, formal
    
    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "contact_name": self.contact_name,
            "message_count": len(self.messages),
            "unread_count": len(self.unread_messages),
            "my_message_count": self.my_message_count,
            "their_message_count": self.their_message_count,
            "avg_my_message_length": round(self.avg_my_message_length, 1),
            "my_messages_per_turn": round(self.my_messages_per_turn, 2),
            "my_emoji_usage": self.my_emoji_usage,
            "formality_level": self.formality_level,
        }


def apple_timestamp_to_datetime(ts: int) -> Optional[datetime]:
    """Convert Apple's nanosecond timestamp to datetime."""
    if ts is None or ts == 0:
        return None
    seconds = ts / 1_000_000_000
    return APPLE_EPOCH + timedelta(seconds=seconds)


def get_conversation_history(
    phone: str, 
    limit: int = 30,
    include_unread_only: bool = False
) -> List[Message]:
    """
    Fetch recent messages with a specific phone number.
    
    ⛔ READ ONLY - No send capability.
    
    Args:
        phone: Phone number to look up
        limit: Maximum messages to return
        include_unread_only: If True, only return unread messages
        
    Returns:
        List of Message objects, oldest first
    """
    if not os.path.exists(MESSAGES_DB):
        return []
    
    try:
        # Open READ ONLY
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        # Normalize phone for matching
        phone_digits = ''.join(c for c in phone if c.isdigit())
        phone_patterns = [
            phone,
            f"+{phone_digits}",
            phone_digits,
            phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        ]
        
        # Build query
        placeholders = ','.join(['?' for _ in phone_patterns * 2])
        
        query = f"""
        SELECT 
            m.rowid as message_id,
            m.guid as message_guid,
            m.text,
            m.date as timestamp,
            m.is_from_me,
            m.is_read,
            h.id as sender_id,
            m.service
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        WHERE (h.id IN ({','.join(['?' for _ in phone_patterns])})
               OR h.uncanonicalized_id IN ({','.join(['?' for _ in phone_patterns])}))
          AND m.text IS NOT NULL
          AND m.text != ''
          {"AND m.is_read = 0 AND m.is_from_me = 0" if include_unread_only else ""}
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        params = phone_patterns + phone_patterns + [limit]
        cursor = conn.execute(query, params)
        
        messages = []
        for row in cursor:
            ts = apple_timestamp_to_datetime(row["timestamp"])
            if ts:
                msg = Message(
                    id=row["message_id"],
                    guid=row["message_guid"],
                    text=row["text"],
                    timestamp=ts,
                    is_from_me=bool(row["is_from_me"]),
                    sender=row["sender_id"] or phone,
                    service=row["service"] or "iMessage"
                )
                messages.append(msg)
        
        conn.close()
        
        # Return in chronological order (oldest first)
        messages.reverse()
        return messages
        
    except Exception as e:
        print(f"Error fetching conversation: {e}")
        return []


def analyze_my_patterns(messages: List[Message]) -> Dict:
    """
    Analyze my communication patterns from message history.
    
    Returns dict with:
    - avg_message_length
    - messages_per_turn (how many I send in a row)
    - emoji_usage
    - typical_greeting
    - formality_level
    """
    my_messages = [m for m in messages if m.is_from_me]
    
    if not my_messages:
        return {
            "avg_message_length": 0,
            "messages_per_turn": 1.0,
            "emoji_usage": "none",
            "typical_greeting": "",
            "formality_level": "casual"
        }
    
    # Average message length
    total_length = sum(len(m.text) for m in my_messages)
    avg_length = total_length / len(my_messages)
    
    # Messages per turn (count consecutive messages from me)
    turns = []
    current_turn = 0
    for msg in messages:
        if msg.is_from_me:
            current_turn += 1
        else:
            if current_turn > 0:
                turns.append(current_turn)
                current_turn = 0
    if current_turn > 0:
        turns.append(current_turn)
    
    avg_per_turn = sum(turns) / len(turns) if turns else 1.0
    
    # Emoji usage
    emoji_count = 0
    for m in my_messages:
        # Simple emoji detection (extended Unicode ranges)
        emoji_count += sum(1 for c in m.text if ord(c) > 0x1F300)
    
    emoji_ratio = emoji_count / len(my_messages)
    if emoji_ratio == 0:
        emoji_usage = "none"
    elif emoji_ratio < 0.3:
        emoji_usage = "low"
    elif emoji_ratio < 1.0:
        emoji_usage = "medium"
    else:
        emoji_usage = "high"
    
    # Typical greeting (first word of messages)
    greetings = {}
    for m in my_messages:
        first_word = m.text.split()[0].lower() if m.text.split() else ""
        if first_word in ['hey', 'hi', 'hello', 'yo', 'sup', 'haha', 'lol']:
            greetings[first_word] = greetings.get(first_word, 0) + 1
    
    typical_greeting = max(greetings, key=greetings.get) if greetings else ""
    
    # Formality (based on punctuation, capitalization, word choice)
    formal_indicators = 0
    for m in my_messages:
        if m.text[0].isupper():
            formal_indicators += 0.5
        if m.text.endswith('.') or m.text.endswith('!'):
            formal_indicators += 0.5
        if any(word in m.text.lower() for word in ['please', 'thank', 'appreciate', 'regards']):
            formal_indicators += 1
    
    formality_score = formal_indicators / len(my_messages)
    if formality_score < 0.5:
        formality_level = "casual"
    elif formality_score < 1.5:
        formality_level = "neutral"
    else:
        formality_level = "formal"
    
    return {
        "avg_message_length": avg_length,
        "messages_per_turn": avg_per_turn,
        "emoji_usage": emoji_usage,
        "typical_greeting": typical_greeting,
        "formality_level": formality_level
    }


def build_conversation_context(
    phone: str,
    contact_name: Optional[str] = None,
    message_limit: int = 30
) -> ConversationContext:
    """
    Build full conversation context for draft generation.
    
    ⛔ READ ONLY - No send capability.
    
    Args:
        phone: Phone number
        contact_name: Optional contact name
        message_limit: How many messages to fetch for context
        
    Returns:
        ConversationContext with all relevant data
    """
    # Fetch all recent messages
    messages = get_conversation_history(phone, limit=message_limit)
    
    # Fetch unread messages specifically
    unread = get_conversation_history(phone, limit=20, include_unread_only=True)
    
    # Build context
    context = ConversationContext(
        phone=phone,
        contact_name=contact_name,
        messages=messages,
        unread_messages=unread,
        total_messages=len(messages)
    )
    
    # Count messages by sender
    context.my_message_count = sum(1 for m in messages if m.is_from_me)
    context.their_message_count = len(messages) - context.my_message_count
    
    # Analyze patterns
    patterns = analyze_my_patterns(messages)
    context.avg_my_message_length = patterns["avg_message_length"]
    context.my_messages_per_turn = patterns["messages_per_turn"]
    context.my_emoji_usage = patterns["emoji_usage"]
    context.my_typical_greeting = patterns["typical_greeting"]
    context.formality_level = patterns["formality_level"]
    
    # Their average message length
    their_messages = [m for m in messages if not m.is_from_me]
    if their_messages:
        context.avg_their_message_length = sum(len(m.text) for m in their_messages) / len(their_messages)
    
    return context


def format_messages_for_prompt(messages: List[Message], contact_name: str = "Them") -> str:
    """Format messages for inclusion in the LLM prompt."""
    lines = []
    for msg in messages:
        sender = "Me" if msg.is_from_me else contact_name
        timestamp = msg.timestamp.strftime("%m/%d %I:%M%p")
        lines.append(f"[{timestamp}] {sender}: {msg.text}")
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    
    # Test with a phone number
    if len(sys.argv) > 1:
        phone = sys.argv[1]
        context = build_conversation_context(phone)
        print(json.dumps(context.to_dict(), indent=2))
        print(f"\nLast 5 messages:")
        for msg in context.messages[-5:]:
            sender = "Me" if msg.is_from_me else "Them"
            print(f"  [{sender}] {msg.text[:50]}...")
    else:
        print("Usage: python imessage_context.py <phone_number>")
