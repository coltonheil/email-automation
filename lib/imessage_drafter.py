#!/usr/bin/env python3
"""
iMessage Draft Generator - Uses Opus 4.5 to generate personalized responses

⛔⛔⛔ CRITICAL SAFETY: THIS MODULE GENERATES DRAFTS ONLY ⛔⛔⛔

This module:
- READS conversation context (READ ONLY)
- GENERATES draft text (stored in database)
- POSTS drafts to Slack (for human review)
- NEVER sends any iMessage directly

All responses MUST be manually copied and sent by the human.
If you see any code attempting to send a message, it is a BUG.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL: Import send guard FIRST - blocks all send operations
from send_guard import (
    SendBlockedError, 
    guard_applescript, 
    guard_composio_action,
    guard_api_endpoint,
    BLOCKED_COMPOSIO_ACTIONS
)

from imessage_context import (
    ConversationContext, 
    Message,
    format_messages_for_prompt,
    build_conversation_context
)

# Database path
DB_PATH = Path(__file__).parent.parent / "database" / "emails.db"


@dataclass
class DraftResult:
    """Result of draft generation."""
    success: bool
    draft_messages: List[str]  # May be multiple messages
    model_used: str
    error: Optional[str] = None
    queue_id: Optional[int] = None
    draft_id: Optional[int] = None


def build_opus_prompt(context: ConversationContext) -> str:
    """
    Build the prompt for Opus 4.5 to generate a response.
    
    Includes:
    - Contact info and relationship context
    - My communication patterns with this person
    - Full conversation history
    - Specific unread messages needing response
    """
    contact_display = context.contact_name or context.phone
    
    # Format conversation history
    conversation_text = format_messages_for_prompt(
        context.messages, 
        contact_name=contact_display
    )
    
    # Format unread messages specifically
    unread_text = ""
    if context.unread_messages:
        unread_text = "\n".join([
            f"- \"{m.text}\" (received {m.timestamp.strftime('%I:%M%p')})"
            for m in context.unread_messages
        ])
    
    # Determine expected response format
    if context.my_messages_per_turn >= 2.5:
        response_format = "multiple short messages (2-3 messages)"
    elif context.my_messages_per_turn >= 1.5:
        response_format = "1-2 messages"
    else:
        response_format = "a single message"
    
    prompt = f"""You are helping me (Colton) draft an iMessage response. Your job is to write a reply that sounds EXACTLY like me based on my communication patterns with this person.

## CONTACT
Name: {contact_display}
Phone: {context.phone}

## MY COMMUNICATION STYLE WITH THIS PERSON
- Average message length: {int(context.avg_my_message_length)} characters
- Messages per turn: {context.my_messages_per_turn:.1f} (I typically send {response_format})
- Emoji usage: {context.my_emoji_usage}
- Formality: {context.formality_level}
- Typical greeting: "{context.my_typical_greeting}" (or none)

## CONVERSATION HISTORY (last {len(context.messages)} messages)
{conversation_text}

## UNREAD MESSAGES I NEED TO RESPOND TO
{unread_text if unread_text else "(No specific unread messages - general response needed)"}

## INSTRUCTIONS
1. Write a response that sounds EXACTLY like my other messages in this conversation
2. Match my typical message length and style with this person
3. If I usually send multiple messages in a row, do the same
4. Use emojis only if I typically use them with this person
5. Be natural and conversational - this should be indistinguishable from my real messages
6. Directly address what they said/asked
7. Keep the same energy and tone as my previous messages

## OUTPUT FORMAT
{"If I typically send multiple messages:" if context.my_messages_per_turn >= 1.5 else ""}
MESSAGE 1: <first message>
MESSAGE 2: <second message if needed>

{"If single message:" if context.my_messages_per_turn < 1.5 else ""}
MESSAGE: <your draft>

IMPORTANT: Provide ONLY the message text. No explanations, no "Here's a draft:", just the message(s)."""

    return prompt


def parse_draft_response(response_text: str) -> List[str]:
    """Parse the LLM response into individual messages."""
    messages = []
    
    # Clean up response
    text = response_text.strip()
    
    # Check for numbered messages
    if "MESSAGE 1:" in text or "MESSAGE:" in text:
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("MESSAGE"):
                # Extract the message content after the colon
                if ":" in line:
                    msg = line.split(":", 1)[1].strip()
                    if msg:
                        messages.append(msg)
    else:
        # Single message, no formatting
        if text:
            messages.append(text)
    
    return messages


def store_draft(
    phone: str,
    contact_name: Optional[str],
    draft_messages: List[str],
    original_messages: List[Message],
    model_used: str = "claude-opus-4.5"
) -> int:
    """
    Store generated draft in database.
    
    ⛔ This only STORES the draft. NO SENDING.
    
    Returns: draft_id
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Ensure tables exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS imessage_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            contact_name TEXT,
            original_messages TEXT,
            draft_messages TEXT,
            message_count INTEGER,
            status TEXT DEFAULT 'pending',
            model_used TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            approved_at TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            sent_at TEXT
        )
    ''')
    
    now = datetime.now().isoformat()
    
    # Store original messages as JSON
    original_json = json.dumps([
        {"text": m.text, "timestamp": m.timestamp.isoformat(), "is_from_me": m.is_from_me}
        for m in original_messages
    ])
    
    # Store draft messages as JSON
    draft_json = json.dumps(draft_messages)
    
    cursor = conn.execute('''
        INSERT INTO imessage_drafts 
        (phone, contact_name, original_messages, draft_messages, message_count, model_used, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (phone, contact_name, original_json, draft_json, len(draft_messages), model_used, now))
    
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return draft_id


def format_for_slack(
    phone: str,
    contact_name: Optional[str],
    original_messages: List[Message],
    draft_messages: List[str],
    draft_id: int
) -> str:
    """Format draft for Slack notification."""
    contact_display = contact_name or phone
    
    # Format original messages
    original_text = "\n".join([
        f"> {m.text}" for m in original_messages[-3:]  # Last 3 unread
    ])
    
    # Format draft messages
    if len(draft_messages) == 1:
        draft_text = draft_messages[0]
    else:
        draft_text = "\n".join([
            f"*{i+1}.* {msg}" for i, msg in enumerate(draft_messages)
        ])
    
    return f"""📱 *iMessage Draft Ready*

*From:* {contact_display}
*Phone:* {phone}

━━━━━━━━━━━━━━━━━━━
📨 *Their message(s):*
{original_text}

━━━━━━━━━━━━━━━━━━━
✏️ *Draft response:*
{draft_text}

━━━━━━━━━━━━━━━━━━━
📋 Draft ID: {draft_id}

⛔ *REMINDER:* Copy and send manually from Messages.app"""


class iMessageDrafter:
    """
    iMessage draft generator using Opus 4.5.
    
    ⛔⛔⛔ SAFETY: DRAFT ONLY - NO SEND CAPABILITY ⛔⛔⛔
    """
    
    def __init__(self):
        # Verify send guards are active
        from send_guard import verify_guards_active
        if not verify_guards_active():
            raise RuntimeError("Send guards not active! Refusing to start.")
    
    def generate_draft(
        self,
        context: ConversationContext,
        use_opus: bool = True
    ) -> DraftResult:
        """
        Generate a draft response using Opus 4.5.
        
        ⛔ DRAFT ONLY - Returns text for human review.
           NEVER sends any message.
        
        Args:
            context: Full conversation context
            use_opus: If True, queue for Opus 4.5 (via Clawdbot)
            
        Returns:
            DraftResult with generated messages
        """
        # Build prompt
        prompt = build_opus_prompt(context)
        
        if use_opus:
            # Queue for Clawdbot/Opus 4.5 processing
            return self._queue_for_opus(context, prompt)
        else:
            # This branch should not be used - Opus is required
            return DraftResult(
                success=False,
                draft_messages=[],
                model_used="none",
                error="Opus 4.5 is required for draft generation"
            )
    
    def _queue_for_opus(
        self,
        context: ConversationContext,
        prompt: str
    ) -> DraftResult:
        """
        Queue the draft request for Opus 4.5 processing.
        Clawdbot will pick this up and generate the draft.
        """
        conn = sqlite3.connect(DB_PATH)
        
        # Ensure queue table exists
        conn.execute('''
            CREATE TABLE IF NOT EXISTS imessage_opus_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                contact_name TEXT,
                prompt TEXT NOT NULL,
                context_json TEXT,
                unread_message_ids TEXT,
                status TEXT DEFAULT 'pending',
                result_json TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            )
        ''')
        
        now = datetime.now().isoformat()
        
        # Store context as JSON
        context_json = json.dumps({
            "phone": context.phone,
            "contact_name": context.contact_name,
            "message_count": len(context.messages),
            "unread_count": len(context.unread_messages),
            "my_patterns": {
                "avg_length": context.avg_my_message_length,
                "messages_per_turn": context.my_messages_per_turn,
                "emoji_usage": context.my_emoji_usage,
                "formality": context.formality_level,
                "greeting": context.my_typical_greeting
            }
        })
        
        # Store unread message IDs
        unread_ids = json.dumps([m.id for m in context.unread_messages])
        
        cursor = conn.execute('''
            INSERT INTO imessage_opus_queue 
            (phone, contact_name, prompt, context_json, unread_message_ids, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ''', (context.phone, context.contact_name, prompt, context_json, unread_ids, now))
        
        queue_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return DraftResult(
            success=True,
            draft_messages=[],
            model_used="claude-opus-4.5 (queued)",
            queue_id=queue_id
        )


def get_pending_opus_queue(limit: int = 10) -> List[Dict]:
    """Get pending items from the Opus queue for Clawdbot to process."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT * FROM imessage_opus_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT ?
    ''', (limit,))
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return items


def complete_opus_queue_item(queue_id: int, draft_messages: List[str], model: str = "claude-opus-4.5") -> int:
    """
    Mark a queue item as complete and store the draft.
    
    ⛔ STORES DRAFT ONLY - NO SENDING
    
    Returns: draft_id
    """
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    
    # Get queue item details
    cursor = conn.execute(
        'SELECT phone, contact_name, context_json FROM imessage_opus_queue WHERE id = ?',
        (queue_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Queue item {queue_id} not found")
    
    phone, contact_name, context_json = row
    
    # Store the draft
    draft_json = json.dumps(draft_messages)
    
    cursor = conn.execute('''
        INSERT INTO imessage_drafts 
        (phone, contact_name, draft_messages, message_count, model_used, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    ''', (phone, contact_name, draft_json, len(draft_messages), model, now))
    
    draft_id = cursor.lastrowid
    
    # Update queue item
    conn.execute('''
        UPDATE imessage_opus_queue
        SET status = 'completed', result_json = ?, processed_at = ?
        WHERE id = ?
    ''', (draft_json, now, queue_id))
    
    conn.commit()
    conn.close()
    
    return draft_id


def fail_opus_queue_item(queue_id: int, error_message: str):
    """Mark a queue item as failed."""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    
    conn.execute('''
        UPDATE imessage_opus_queue
        SET status = 'failed', error_message = ?, processed_at = ?
        WHERE id = ?
    ''', (error_message, now, queue_id))
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Test with a phone number
    import json
    
    if len(sys.argv) > 1:
        phone = sys.argv[1]
        print(f"Building context for {phone}...")
        
        context = build_conversation_context(phone, message_limit=30)
        print(f"Found {len(context.messages)} messages, {len(context.unread_messages)} unread")
        print(f"My patterns: {context.my_messages_per_turn:.1f} msgs/turn, {context.my_emoji_usage} emojis, {context.formality_level}")
        
        print("\nGenerating prompt...")
        prompt = build_opus_prompt(context)
        print(f"Prompt length: {len(prompt)} chars")
        
        print("\n--- PROMPT PREVIEW ---")
        print(prompt[:1500] + "...")
    else:
        print("Usage: python imessage_drafter.py <phone_number>")
        print("\n⛔ REMINDER: This module is DRAFT ONLY. No messages will ever be sent.")
