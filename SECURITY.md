# SECURITY.md - Message Automation Security Policy

## ⛔ ABSOLUTE RULE: NO AUTOMATIC SENDING

This email-automation system is **DRAFT-ONLY**. It must **NEVER** send any message automatically.

All responses must be:
1. Generated as drafts
2. Reviewed by the human
3. Manually copied and sent from the native app (Mail, Messages, etc.)

---

## 🔒 Security Barriers Implemented

### 1. Code-Level Blocks (`lib/send_guard.py`)

The `send_guard` module provides runtime protection:

```python
# Blocked Composio actions (emails)
GMAIL_SEND_EMAIL, GMAIL_REPLY, OUTLOOK_SEND_EMAIL, etc.

# Blocked AppleScript commands (iMessage)
"send message", "send to", "make new outgoing message"

# Blocked BlueBubbles endpoints
"/api/v1/message/send", "sendMessage", etc.
```

**How it works:**
- Imported automatically by email_fetcher.py
- Patches `subprocess.run` and `os.system` to block AppleScript sends
- `guard_composio_action()` called before every Composio API call
- Raises `SendBlockedError` if any send operation is attempted

### 2. Composio Configuration

**DO NOT configure these Composio actions:**
- `GMAIL_SEND_EMAIL`
- `GMAIL_REPLY_TO_EMAIL`
- `OUTLOOK_SEND_MAIL`
- `OUTLOOK_REPLY_MAIL`
- Any action containing "SEND", "REPLY", "FORWARD"

**Only these READ actions are used:**
- `GMAIL_FETCH_EMAILS`
- `GMAIL_GET_MESSAGE`
- `OUTLOOK_LIST_MESSAGES`
- `OUTLOOK_GET_MESSAGE`

### 3. iMessage Protection

**fetch_imessages.py:**
- Opens Messages database in READ-ONLY mode: `sqlite3.connect("file:...?mode=ro", uri=True)`
- No AppleScript commands
- No BlueBubbles integration

**draft_imessage_response.py:**
- Only creates database records
- No send functionality at all
- All drafts pushed to Slack for human review

### 4. API Route Protection

**Web app routes (`/api/*`):**
- No send endpoints exist
- `PATCH /api/drafts/:id` only updates status (approve/reject/mark-sent)
- "Mark as sent" only records that human manually sent it
- No actual message transmission code

### 5. Slack Notifications

Drafts are pushed to Slack for review:
- `#exec-approvals` for urgent emails
- `#repo-email-automation` for AI edit completions

The human copies the draft and manually pastes it into their email/message client.

---

## 🚨 What Gets Blocked

### Composio Actions
```
GMAIL_SEND_EMAIL        ❌ BLOCKED
GMAIL_REPLY             ❌ BLOCKED
OUTLOOK_SEND_MAIL       ❌ BLOCKED
OUTLOOK_REPLY_MAIL      ❌ BLOCKED
*_SEND_*                ❌ BLOCKED
*_REPLY_*               ❌ BLOCKED
*_FORWARD_*             ❌ BLOCKED
```

### AppleScript
```applescript
tell application "Messages" to send "Hello"    ❌ BLOCKED
make new outgoing message                       ❌ BLOCKED
```

### BlueBubbles API
```
POST /api/v1/message/send       ❌ BLOCKED
POST /api/v1/message/send/text  ❌ BLOCKED
```

---

## ✅ What Is Allowed

### Read Operations
- Fetch emails from Gmail/Outlook/Instantly
- Read iMessages from Messages.db
- Query sender history
- Analyze email threads

### Draft Operations
- Generate draft responses
- Store drafts in database
- Push drafts to Slack
- Edit/approve/reject drafts

### Status Updates
- Mark draft as "approved"
- Mark draft as "sent" (human confirmed they sent it manually)
- Track draft history

---

## 🔐 How to Verify Security

### Test the guards:
```bash
cd ~/clawd/projects/email-automation
python3 lib/send_guard.py
```

Expected output:
```
✅ GMAIL_SEND_EMAIL blocked correctly
✅ AppleScript send blocked correctly
✅ BlueBubbles send blocked correctly
```

### Check for send code:
```bash
grep -rn "execute_action.*SEND\|osascript.*send\|sendMessage" lib/ scripts/ --include="*.py"
```

Should return no matches.

---

## 🛡️ Modifying This Policy

**DO NOT** modify this policy without explicit human approval.

If you need to change the security model:
1. Document the change in #exec-approvals
2. Get explicit human approval
3. Update this SECURITY.md
4. Update MEMORY.md and AGENTS.md

The current policy was established on **2026-01-30** by explicit user request.

---

## 📋 Checklist for New Features

Before adding any new feature, verify:

- [ ] No Composio send actions used
- [ ] No AppleScript send commands
- [ ] No BlueBubbles send endpoints
- [ ] No `requests.post()` to any messaging API
- [ ] All outputs are drafts, not sent messages
- [ ] Draft review happens in Slack or web dashboard
- [ ] Human must manually copy and send

---

*Last updated: 2026-01-30*
*Policy owner: Colton Heil*
