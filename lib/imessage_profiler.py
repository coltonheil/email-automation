#!/usr/bin/env python3
"""
iMessage Contact Profiler - Builds communication profiles per contact

⛔ SAFETY: This module is READ-ONLY.
   It only analyzes message history to build profiles.
   NO SEND CAPABILITY whatsoever.

Profiles include:
- Average message length
- Messages per turn (do you send 1 or 3-4 in a row?)
- Emoji usage patterns
- Formality level
- Typical greetings/signoffs
- Common topics
- Response time patterns
"""

import sqlite3
import json
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL: Import send guard
from send_guard import SendBlockedError

# Paths
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "emails.db"
CONFIG_PATH = PROJECT_ROOT / "config" / "profile_contacts.json"
APPLE_EPOCH = datetime(2001, 1, 1)


@dataclass
class ContactProfile:
    """Communication profile for a contact."""
    phone: str
    contact_name: str
    
    # Message patterns
    total_messages_analyzed: int = 0
    my_message_count: int = 0
    their_message_count: int = 0
    
    # Length patterns
    my_avg_message_length: float = 0.0
    my_median_message_length: int = 0
    their_avg_message_length: float = 0.0
    
    # Turn patterns (messages in a row)
    my_avg_messages_per_turn: float = 1.0
    my_max_messages_per_turn: int = 1
    
    # Style patterns
    my_emoji_frequency: str = "none"  # none, low, medium, high
    my_emoji_examples: List[str] = None
    my_formality_score: int = 5  # 1-10 (1=very casual, 10=very formal)
    my_typical_greeting: str = ""
    my_typical_signoff: str = ""
    
    # Timing
    my_avg_response_time_hours: float = 0.0
    their_avg_response_time_hours: float = 0.0
    
    # Topics (auto-detected)
    common_topics: List[str] = None
    
    # Relationship hints
    relationship_type: str = "unknown"  # personal, business, family, tenant, etc.
    
    # Meta
    last_analyzed_at: str = ""
    last_message_at: str = ""
    profile_notes: str = ""
    
    def __post_init__(self):
        if self.my_emoji_examples is None:
            self.my_emoji_examples = []
        if self.common_topics is None:
            self.common_topics = []
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_prompt_summary(self) -> str:
        """Format profile for inclusion in LLM prompt."""
        return f"""Communication Style with {self.contact_name}:
- My typical message length: {int(self.my_avg_message_length)} characters
- Messages per turn: {self.my_avg_messages_per_turn:.1f} (I send {self._turn_description()})
- Emoji usage: {self.my_emoji_frequency}{self._emoji_examples()}
- Formality: {self._formality_description()} ({self.my_formality_score}/10)
- Typical greeting: "{self.my_typical_greeting}" 
- Relationship: {self.relationship_type}
- Topics we discuss: {', '.join(self.common_topics[:5]) if self.common_topics else 'various'}"""
    
    def _turn_description(self) -> str:
        if self.my_avg_messages_per_turn >= 3:
            return "multiple messages in a row (3+)"
        elif self.my_avg_messages_per_turn >= 2:
            return "2-3 messages per response"
        elif self.my_avg_messages_per_turn >= 1.5:
            return "1-2 messages"
        else:
            return "single messages"
    
    def _emoji_examples(self) -> str:
        if self.my_emoji_examples:
            return f" (commonly: {' '.join(self.my_emoji_examples[:3])})"
        return ""
    
    def _formality_description(self) -> str:
        if self.my_formality_score <= 3:
            return "very casual"
        elif self.my_formality_score <= 5:
            return "casual"
        elif self.my_formality_score <= 7:
            return "neutral"
        else:
            return "formal"


def apple_timestamp_to_datetime(ts: int) -> Optional[datetime]:
    if ts is None or ts == 0:
        return None
    return APPLE_EPOCH + timedelta(seconds=ts / 1_000_000_000)


def get_messages_for_contact(phone: str, limit: int = 500) -> List[dict]:
    """
    Fetch messages with a contact for analysis.
    
    ⛔ READ ONLY
    """
    if not os.path.exists(MESSAGES_DB):
        return []
    
    conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    
    # Normalize phone
    phone_digits = ''.join(c for c in phone if c.isdigit())
    patterns = [phone, f"+{phone_digits}", phone_digits[-10:]]
    
    query = """
    SELECT 
        m.rowid as id,
        m.text,
        m.date as timestamp,
        m.is_from_me,
        m.service
    FROM message m
    JOIN handle h ON m.handle_id = h.rowid
    WHERE (h.id IN (?,?,?) OR h.uncanonicalized_id IN (?,?,?))
      AND m.text IS NOT NULL
      AND m.text != ''
    ORDER BY m.date DESC
    LIMIT ?
    """
    
    cursor = conn.execute(query, patterns + patterns + [limit])
    
    messages = []
    for row in cursor:
        ts = apple_timestamp_to_datetime(row["timestamp"])
        if ts:
            messages.append({
                "id": row["id"],
                "text": row["text"],
                "timestamp": ts,
                "is_from_me": bool(row["is_from_me"]),
            })
    
    conn.close()
    messages.reverse()  # Chronological order
    return messages


def extract_emojis(text: str) -> List[str]:
    """Extract emoji characters from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.findall(text)


def analyze_turns(messages: List[dict]) -> Tuple[float, int]:
    """
    Analyze how many messages are sent in a row (per turn).
    
    Returns: (avg_per_turn, max_per_turn)
    """
    turns = []
    current_turn = 0
    last_from_me = None
    
    for msg in messages:
        if msg["is_from_me"]:
            if last_from_me == True:
                current_turn += 1
            else:
                if current_turn > 0:
                    turns.append(current_turn)
                current_turn = 1
        else:
            if current_turn > 0:
                turns.append(current_turn)
                current_turn = 0
        
        last_from_me = msg["is_from_me"]
    
    if current_turn > 0:
        turns.append(current_turn)
    
    if not turns:
        return 1.0, 1
    
    return sum(turns) / len(turns), max(turns)


def detect_formality(messages: List[dict]) -> int:
    """
    Detect formality level from my messages.
    
    Returns score 1-10 (1=very casual, 10=very formal)
    """
    my_messages = [m for m in messages if m["is_from_me"]]
    if not my_messages:
        return 5
    
    score = 5.0
    
    for msg in my_messages:
        text = msg["text"]
        
        # Casual indicators (-1 each)
        if text.lower().startswith(('yo ', 'hey ', 'sup ', 'lol', 'haha', 'lmao')):
            score -= 0.1
        if text == text.lower():  # All lowercase
            score -= 0.05
        if '!!' in text or '??' in text:
            score -= 0.05
        
        # Formal indicators (+1 each)
        if text[0].isupper() and text[-1] in '.!?':
            score += 0.05
        if any(word in text.lower() for word in ['please', 'thank', 'appreciate', 'regards', 'sincerely']):
            score += 0.2
        if any(word in text.lower() for word in ['hello', 'good morning', 'good evening']):
            score += 0.1
    
    return max(1, min(10, int(score)))


def detect_greeting(messages: List[dict]) -> str:
    """Detect my typical greeting."""
    my_messages = [m for m in messages if m["is_from_me"]]
    
    greetings = Counter()
    greeting_words = ['hey', 'hi', 'hello', 'yo', 'sup', 'haha', 'lol', 'nice', 'cool', 'ok', 'okay']
    
    for msg in my_messages:
        words = msg["text"].lower().split()
        if words:
            first = words[0].rstrip('!,.')
            if first in greeting_words:
                greetings[first] += 1
    
    if greetings:
        return greetings.most_common(1)[0][0]
    return ""


def detect_topics(messages: List[dict]) -> List[str]:
    """Detect common topics from conversation."""
    all_text = ' '.join(m["text"].lower() for m in messages)
    
    # Topic keywords
    topic_keywords = {
        "property": ["property", "rent", "lease", "apartment", "unit", "tenant", "landlord"],
        "maintenance": ["sink", "toilet", "plumber", "electrician", "repair", "fix", "broken"],
        "work": ["meeting", "call", "project", "deadline", "client", "work"],
        "money": ["payment", "paid", "pay", "invoice", "cost", "price", "$"],
        "scheduling": ["tomorrow", "today", "next week", "schedule", "time", "available"],
        "social": ["dinner", "drinks", "lunch", "hangout", "party", "weekend"],
    }
    
    detected = []
    for topic, keywords in topic_keywords.items():
        if any(kw in all_text for kw in keywords):
            detected.append(topic)
    
    return detected


def detect_relationship(contact_name: str, messages: List[dict]) -> str:
    """Guess relationship type from name and messages."""
    name_lower = contact_name.lower()
    
    # Check name patterns
    if any(x in name_lower for x in ['unit', 'tenant', 'apt', 'apartment']):
        return "tenant"
    if any(x in name_lower for x in ['handyman', 'plumber', 'contractor', 'realtor', 'broker']):
        return "business"
    if any(x in name_lower for x in ['dad', 'mom', 'brother', 'sister', 'grandma', 'grandpa']):
        return "family"
    
    # Check message patterns
    all_text = ' '.join(m["text"].lower() for m in messages[-50:])
    
    if any(x in all_text for x in ['love you', 'miss you', 'babe', 'baby', '❤️', '💕']):
        return "partner"
    if any(x in all_text for x in ['rent', 'lease', 'property', 'unit']):
        return "tenant"
    if any(x in all_text for x in ['invoice', 'quote', 'estimate', 'job']):
        return "business"
    
    return "personal"


def build_profile(phone: str, contact_name: str) -> ContactProfile:
    """
    Build a full communication profile for a contact.
    
    ⛔ READ ONLY - Only analyzes existing messages
    """
    messages = get_messages_for_contact(phone, limit=500)
    
    profile = ContactProfile(
        phone=phone,
        contact_name=contact_name,
        total_messages_analyzed=len(messages),
        last_analyzed_at=datetime.now().isoformat()
    )
    
    if not messages:
        return profile
    
    # Separate my messages vs theirs
    my_messages = [m for m in messages if m["is_from_me"]]
    their_messages = [m for m in messages if not m["is_from_me"]]
    
    profile.my_message_count = len(my_messages)
    profile.their_message_count = len(their_messages)
    
    if messages:
        profile.last_message_at = messages[-1]["timestamp"].isoformat()
    
    if my_messages:
        # Length analysis
        lengths = [len(m["text"]) for m in my_messages]
        profile.my_avg_message_length = sum(lengths) / len(lengths)
        profile.my_median_message_length = sorted(lengths)[len(lengths) // 2]
        
        # Turn analysis
        profile.my_avg_messages_per_turn, profile.my_max_messages_per_turn = analyze_turns(messages)
        
        # Emoji analysis
        all_emojis = []
        for m in my_messages:
            all_emojis.extend(extract_emojis(m["text"]))
        
        emoji_ratio = len(all_emojis) / len(my_messages)
        if emoji_ratio == 0:
            profile.my_emoji_frequency = "none"
        elif emoji_ratio < 0.2:
            profile.my_emoji_frequency = "low"
        elif emoji_ratio < 0.5:
            profile.my_emoji_frequency = "medium"
        else:
            profile.my_emoji_frequency = "high"
        
        # Most common emojis
        if all_emojis:
            emoji_counts = Counter(all_emojis)
            profile.my_emoji_examples = [e for e, _ in emoji_counts.most_common(5)]
        
        # Formality
        profile.my_formality_score = detect_formality(my_messages)
        
        # Greeting
        profile.my_typical_greeting = detect_greeting(my_messages)
    
    if their_messages:
        their_lengths = [len(m["text"]) for m in their_messages]
        profile.their_avg_message_length = sum(their_lengths) / len(their_lengths)
    
    # Topics and relationship
    profile.common_topics = detect_topics(messages)
    profile.relationship_type = detect_relationship(contact_name, messages)
    
    return profile


def save_profile(profile: ContactProfile):
    """Save profile to database."""
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contact_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            contact_name TEXT,
            profile_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    ''')
    
    now = datetime.now().isoformat()
    profile_json = json.dumps(profile.to_dict())
    
    conn.execute('''
        INSERT INTO contact_profiles (phone, contact_name, profile_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(phone) DO UPDATE SET
            contact_name = excluded.contact_name,
            profile_json = excluded.profile_json,
            updated_at = excluded.updated_at
    ''', (profile.phone, profile.contact_name, profile_json, now))
    
    conn.commit()
    conn.close()


def load_profile(phone: str) -> Optional[ContactProfile]:
    """Load profile from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        'SELECT profile_json FROM contact_profiles WHERE phone = ?',
        (phone,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = json.loads(row[0])
        return ContactProfile(**data)
    return None


def get_profile_contacts() -> List[dict]:
    """Get list of contacts that should have profiles."""
    if not CONFIG_PATH.exists():
        return []
    
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    
    return config.get("contacts", [])


def build_all_profiles() -> List[ContactProfile]:
    """Build profiles for all configured contacts."""
    contacts = get_profile_contacts()
    profiles = []
    
    for contact in contacts:
        phone = contact["phone"]
        name = contact["name"]
        
        print(f"Building profile for {name}...")
        profile = build_profile(phone, name)
        save_profile(profile)
        profiles.append(profile)
    
    return profiles


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="iMessage Contact Profiler (READ ONLY)")
    parser.add_argument("--build-all", action="store_true", help="Build profiles for all configured contacts")
    parser.add_argument("--phone", help="Build/show profile for specific phone")
    parser.add_argument("--list", action="store_true", help="List configured contacts")
    
    args = parser.parse_args()
    
    if args.build_all:
        profiles = build_all_profiles()
        print(f"\n✅ Built {len(profiles)} profiles")
        for p in profiles:
            print(f"  - {p.contact_name}: {p.my_message_count} sent, {p.my_avg_messages_per_turn:.1f} msgs/turn, {p.my_emoji_frequency} emojis")
    
    elif args.phone:
        # Try loading existing
        profile = load_profile(args.phone)
        if not profile:
            from contacts_lookup import lookup_contact
            name = lookup_contact(args.phone) or args.phone
            profile = build_profile(args.phone, name)
        
        print(json.dumps(profile.to_dict(), indent=2, default=str))
        print("\n--- PROMPT SUMMARY ---")
        print(profile.to_prompt_summary())
    
    elif args.list:
        contacts = get_profile_contacts()
        print(f"Configured contacts ({len(contacts)}):")
        for c in contacts:
            print(f"  - {c['name']}: {c['phone']}")
    
    else:
        parser.print_help()
