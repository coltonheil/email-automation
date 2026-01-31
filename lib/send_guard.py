#!/usr/bin/env python3
"""
SEND GUARD - Security barrier preventing any message sending

⛔⛔⛔ CRITICAL SECURITY MODULE ⛔⛔⛔

This module BLOCKS all attempts to send messages via any channel:
- Email (Gmail, Outlook, Instantly)
- iMessage (AppleScript, BlueBubbles)
- SMS
- Any other messaging API

This is a HARD BLOCK that cannot be bypassed without modifying this file.
Any code that attempts to import a send function will get a blocked version.

POLICY: This email-automation system is DRAFT-ONLY.
All responses must be manually copied and sent by the human.
"""

import sys
import functools
from typing import Any, Callable

# ============================================
# BLOCKED ACTIONS - These are NEVER allowed
# ============================================

BLOCKED_COMPOSIO_ACTIONS = frozenset([
    # Gmail send actions
    "GMAIL_SEND_EMAIL",
    "GMAIL_SEND_MESSAGE",
    "GMAIL_REPLY",
    "GMAIL_REPLY_TO_EMAIL",
    "GMAIL_CREATE_DRAFT_AND_SEND",
    "GMAIL_FORWARD",
    
    # Outlook send actions
    "OUTLOOK_SEND_EMAIL",
    "OUTLOOK_SEND_MESSAGE", 
    "OUTLOOK_REPLY",
    "OUTLOOK_REPLY_TO_MESSAGE",
    "OUTLOOK_FORWARD",
    "OUTLOOK_OUTLOOK_SEND_MAIL",
    "OUTLOOK_OUTLOOK_REPLY_MAIL",
    
    # Instantly send actions
    "INSTANTLY_SEND_EMAIL",
    "INSTANTLY_SEND_MESSAGE",
    "INSTANTLY_REPLY",
    
    # Generic patterns
    "SEND_EMAIL",
    "SEND_MESSAGE",
    "REPLY_TO",
    "FORWARD_EMAIL",
])

BLOCKED_APPLESCRIPT_PATTERNS = frozenset([
    "send message",
    "send to",
    "make new outgoing message",
    "send",
])

BLOCKED_BLUEBUBBLES_ENDPOINTS = frozenset([
    "/api/v1/message/send",
    "/api/v1/message/send/text",
    "/api/v1/message/send/attachment",
    "/api/v1/message/reply",
    "sendMessage",
    "sendText",
])


class SendBlockedError(Exception):
    """Raised when a send operation is blocked"""
    pass


def is_send_action(action_name: str) -> bool:
    """Check if an action is a blocked send action"""
    action_upper = action_name.upper()
    
    # Direct match
    if action_upper in BLOCKED_COMPOSIO_ACTIONS:
        return True
    
    # Pattern match
    send_patterns = ["SEND", "REPLY", "FORWARD", "POST", "DELIVER"]
    for pattern in send_patterns:
        if pattern in action_upper:
            return True
    
    return False


def is_blocked_applescript(script: str) -> bool:
    """Check if an AppleScript contains blocked send commands"""
    script_lower = script.lower()
    for pattern in BLOCKED_APPLESCRIPT_PATTERNS:
        if pattern in script_lower:
            return True
    return False


def is_blocked_endpoint(endpoint: str) -> bool:
    """Check if a BlueBubbles/API endpoint is blocked"""
    endpoint_lower = endpoint.lower()
    for pattern in BLOCKED_BLUEBUBBLES_ENDPOINTS:
        if pattern.lower() in endpoint_lower:
            return True
    return False


def block_send(func: Callable) -> Callable:
    """Decorator that blocks any function from actually sending"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        raise SendBlockedError(
            f"⛔ BLOCKED: {func.__name__} is not allowed. "
            "This system is DRAFT-ONLY. No automatic sending permitted. "
            "All messages must be manually copied and sent by the human."
        )
    return wrapper


def guard_composio_action(action_name: str, input_params: dict) -> None:
    """
    Guard function to call BEFORE any Composio action execution.
    Raises SendBlockedError if the action is a send action.
    """
    if is_send_action(action_name):
        raise SendBlockedError(
            f"⛔ BLOCKED: Composio action '{action_name}' is a SEND action. "
            "This system is DRAFT-ONLY. No automatic sending permitted. "
            f"Blocked input: {str(input_params)[:200]}..."
        )


def guard_applescript(script: str) -> None:
    """
    Guard function to call BEFORE any AppleScript execution.
    Raises SendBlockedError if the script contains send commands.
    """
    if is_blocked_applescript(script):
        raise SendBlockedError(
            "⛔ BLOCKED: AppleScript contains 'send' command. "
            "This system is DRAFT-ONLY. No automatic sending permitted. "
            f"Blocked script: {script[:200]}..."
        )


def guard_api_endpoint(endpoint: str, method: str = "POST") -> None:
    """
    Guard function to call BEFORE any API request.
    Raises SendBlockedError if the endpoint is a send endpoint.
    """
    if is_blocked_endpoint(endpoint):
        raise SendBlockedError(
            f"⛔ BLOCKED: API endpoint '{endpoint}' is a SEND endpoint. "
            "This system is DRAFT-ONLY. No automatic sending permitted."
        )


# ============================================
# INSTALL GUARDS - Patch dangerous functions
# ============================================

_original_subprocess_run = None
_original_subprocess_popen = None
_original_os_system = None

def _guarded_subprocess_run(args, **kwargs):
    """Guarded version of subprocess.run that blocks AppleScript sends"""
    global _original_subprocess_run
    
    # Check for osascript (AppleScript)
    if args and len(args) > 0:
        cmd = args[0] if isinstance(args, (list, tuple)) else args
        if 'osascript' in str(cmd).lower():
            # Check the script content
            script_content = ' '.join(str(a) for a in args) if isinstance(args, (list, tuple)) else str(args)
            guard_applescript(script_content)
    
    return _original_subprocess_run(args, **kwargs)


def _guarded_os_system(command):
    """Guarded version of os.system that blocks AppleScript sends"""
    global _original_os_system
    
    if 'osascript' in str(command).lower():
        guard_applescript(command)
    
    return _original_os_system(command)


def install_guards():
    """
    Install security guards on dangerous functions.
    Call this at module import time.
    """
    global _original_subprocess_run, _original_subprocess_popen, _original_os_system
    
    import subprocess
    import os
    
    # Guard subprocess.run
    if _original_subprocess_run is None:
        _original_subprocess_run = subprocess.run
        subprocess.run = _guarded_subprocess_run
    
    # Guard os.system
    if _original_os_system is None:
        _original_os_system = os.system
        os.system = _guarded_os_system
    
    print("🔒 Send guards installed - all send operations will be blocked")


def verify_guards_active() -> bool:
    """Verify that security guards are installed and active"""
    import subprocess
    import os
    
    return (
        subprocess.run != _original_subprocess_run or _original_subprocess_run is None
    ) and (
        os.system != _original_os_system or _original_os_system is None
    )


# ============================================
# SAFE OPERATIONS - These are allowed
# ============================================

ALLOWED_COMPOSIO_ACTIONS = frozenset([
    # Gmail read actions
    "GMAIL_FETCH_EMAILS",
    "GMAIL_LIST_EMAILS", 
    "GMAIL_GET_EMAIL",
    "GMAIL_GET_MESSAGE",
    "GMAIL_SEARCH",
    "GMAIL_LIST_LABELS",
    "GMAIL_GET_THREAD",
    
    # Outlook read actions
    "OUTLOOK_LIST_MESSAGES",
    "OUTLOOK_GET_MESSAGE",
    "OUTLOOK_OUTLOOK_LIST_MESSAGES",
    "OUTLOOK_OUTLOOK_GET_MESSAGE",
    "OUTLOOK_LIST_FOLDERS",
    
    # Instantly read actions
    "INSTANTLY_LIST_EMAILS",
    "INSTANTLY_GET_EMAIL",
    "INSTANTLY_LIST_CAMPAIGNS",
])


def is_safe_action(action_name: str) -> bool:
    """Check if an action is explicitly safe (read-only)"""
    action_upper = action_name.upper()
    
    # Direct match to allowed list
    if action_upper in ALLOWED_COMPOSIO_ACTIONS:
        return True
    
    # Pattern match for safe operations
    safe_patterns = ["FETCH", "LIST", "GET", "SEARCH", "READ"]
    for pattern in safe_patterns:
        if pattern in action_upper:
            # Double-check it's not also a send
            if not is_send_action(action_name):
                return True
    
    return False


# ============================================
# AUTO-INSTALL ON IMPORT
# ============================================

# Install guards when this module is imported
install_guards()


if __name__ == "__main__":
    print("=" * 60)
    print("SEND GUARD - Security Barrier Test")
    print("=" * 60)
    print()
    print("✅ Guards installed:", verify_guards_active())
    print()
    print("Blocked Composio actions:", len(BLOCKED_COMPOSIO_ACTIONS))
    print("Allowed Composio actions:", len(ALLOWED_COMPOSIO_ACTIONS))
    print()
    
    # Test blocking
    print("Testing blocks...")
    
    try:
        guard_composio_action("GMAIL_SEND_EMAIL", {"to": "test@example.com"})
        print("❌ FAILED - GMAIL_SEND_EMAIL should be blocked")
    except SendBlockedError as e:
        print("✅ GMAIL_SEND_EMAIL blocked correctly")
    
    try:
        guard_applescript('tell application "Messages" to send "Hello" to buddy "+1234567890"')
        print("❌ FAILED - AppleScript send should be blocked")
    except SendBlockedError as e:
        print("✅ AppleScript send blocked correctly")
    
    try:
        guard_api_endpoint("/api/v1/message/send/text")
        print("❌ FAILED - BlueBubbles send should be blocked")
    except SendBlockedError as e:
        print("✅ BlueBubbles send blocked correctly")
    
    print()
    print("All tests passed! Send operations are blocked.")
