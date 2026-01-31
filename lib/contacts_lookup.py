#!/usr/bin/env python3
"""
Contacts Lookup - Map phone numbers to contact names

⛔ SAFETY: This is READ-ONLY access to Contacts.
   Uses AppleScript to query Contacts app.
   No modification capability.
"""

import subprocess
import re
import json
from typing import Dict, Optional
from pathlib import Path

# Cache file for contacts
CACHE_PATH = Path(__file__).parent.parent / 'data' / 'contacts_cache.json'

def normalize_phone(phone: str) -> str:
    """Normalize phone number to just digits for comparison."""
    return re.sub(r'[^\d]', '', phone)

def fetch_contacts_from_app() -> Dict[str, str]:
    """
    Fetch all contacts with phone numbers from Contacts app.
    Returns dict mapping normalized phone -> name
    
    READ ONLY - uses AppleScript to query Contacts.
    """
    script = '''
    tell application "Contacts"
        set output to ""
        repeat with p in people
            try
                set personName to name of p
                repeat with ph in phones of p
                    set phoneNum to value of ph
                    set output to output & personName & "|||" & phoneNum & "\\n"
                end repeat
            end try
        end repeat
        return output
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr}")
            return {}
        
        contacts = {}
        for line in result.stdout.strip().split('\n'):
            if '|||' in line:
                parts = line.split('|||')
                if len(parts) == 2:
                    name, phone = parts
                    normalized = normalize_phone(phone)
                    if normalized and len(normalized) >= 10:
                        # Store with last 10 digits as key (handles country codes)
                        key = normalized[-10:]
                        contacts[key] = name.strip()
        
        return contacts
        
    except subprocess.TimeoutExpired:
        print("Timeout fetching contacts")
        return {}
    except Exception as e:
        print(f"Error fetching contacts: {e}")
        return {}

def save_cache(contacts: Dict[str, str]) -> None:
    """Save contacts to cache file."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(contacts, f, indent=2)

def load_cache() -> Dict[str, str]:
    """Load contacts from cache file."""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except:
            return {}
    return {}

def refresh_cache() -> Dict[str, str]:
    """Refresh the contacts cache from Contacts app."""
    contacts = fetch_contacts_from_app()
    if contacts:
        save_cache(contacts)
    return contacts

def lookup_contact(phone: str, use_cache: bool = True) -> Optional[str]:
    """
    Look up a contact name by phone number.
    
    Args:
        phone: Phone number (any format)
        use_cache: Whether to use cached contacts (default True)
        
    Returns:
        Contact name or None if not found
    """
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return None
    
    # Use last 10 digits for lookup
    key = normalized[-10:]
    
    if use_cache:
        contacts = load_cache()
        if not contacts:
            contacts = refresh_cache()
    else:
        contacts = fetch_contacts_from_app()
    
    return contacts.get(key)

def lookup_multiple(phones: list, use_cache: bool = True) -> Dict[str, Optional[str]]:
    """Look up multiple phone numbers at once."""
    if use_cache:
        contacts = load_cache()
        if not contacts:
            contacts = refresh_cache()
    else:
        contacts = fetch_contacts_from_app()
    
    results = {}
    for phone in phones:
        normalized = normalize_phone(phone)
        if normalized and len(normalized) >= 10:
            key = normalized[-10:]
            results[phone] = contacts.get(key)
        else:
            results[phone] = None
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--refresh":
            print("Refreshing contacts cache...")
            contacts = refresh_cache()
            print(f"Cached {len(contacts)} contacts")
        elif sys.argv[1] == "--lookup":
            phone = sys.argv[2] if len(sys.argv) > 2 else ""
            name = lookup_contact(phone)
            print(f"{phone} -> {name or 'Not found'}")
        else:
            # Assume it's a phone number to look up
            name = lookup_contact(sys.argv[1])
            print(f"{sys.argv[1]} -> {name or 'Not found'}")
    else:
        # Default: refresh and show count
        print("Refreshing contacts cache...")
        contacts = refresh_cache()
        print(f"Cached {len(contacts)} contacts")
        print(json.dumps({"contacts_count": len(contacts)}, indent=2))
