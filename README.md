# Email Automation System

**Unified inbox triage across 8 email accounts with intelligent priority scoring.**

## Overview

This system aggregates emails from multiple providers into a single prioritized triage queue:

- **1 Gmail account**
- **3 Outlook accounts**
- **1 Instantly workspace** (4 sending accounts)

**Total: 8 inboxes monitored**

## Quick Start

### Fetch Unread Emails

```bash
cd ~/clawd/projects/email-automation
export COMPOSIO_API_KEY=<your-key>
python3 scripts/fetch_all_emails.py --mode unread
```

### Fetch Recent Emails (Last 24 Hours)

```bash
python3 scripts/fetch_all_emails.py --mode recent --hours 24
```

### Save Results to JSON

```bash
python3 scripts/fetch_all_emails.py --mode unread --output data/triage_queue.json
```

## Priority Scoring

Emails are scored 0-100 and categorized:

- **Urgent (80-100):** VIP senders, action required, payment/security alerts
- **Normal (40-79):** Standard emails, moderate importance
- **Low (0-39):** Newsletters, marketing, old emails

### Scoring Factors

**Boosts (+):**
- VIP sender: +30
- Urgent keywords (urgent, ASAP, deadline): +20
- Marked important by provider: +15
- Unread: +10
- Has attachments: +5
- Recency (last hour): +15

**Penalties (-):**
- Spam indicators: -30
- Older than 7 days: -20
- Newsletter/marketing: -15

## Configuration

Edit `config/accounts.json` to customize:

```json
{
  "gmail": [...],
  "outlook": [...],
  "instantly": [...]
}
```

Each account has:
- `id`: Unique identifier
- `composio_account_id`: Composio connected account ID
- `priority_weight`: Multiplier for this account's emails
- `check_frequency_hours`: How often to check (used by cron)

## Usage Examples

### Check All Accounts (Unread Only)

```bash
python3 scripts/fetch_all_emails.py --mode unread --limit 100
```

### Last 6 Hours (Recent Activity)

```bash
python3 scripts/fetch_all_emails.py --mode recent --hours 6
```

### Output JSON for Processing

```bash
python3 scripts/fetch_all_emails.py --mode unread --json > data/queue.json
```

## Architecture

### Components

1. **`lib/email_fetcher.py`** - Fetches emails from Composio
2. **`lib/email_normalizer.py`** - Standardizes email format across providers
3. **`lib/priority_scorer.py`** - Calculates priority scores
4. **`scripts/fetch_all_emails.py`** - Main aggregation script

### Data Flow

```
Gmail/Outlook/Instantly → Fetch → Normalize → Score → Deduplicate → Sort → Output
```

## Features

✅ **Multi-provider support** (Gmail, Outlook, Instantly)  
✅ **Intelligent priority scoring** (0-100 scale)  
✅ **Automatic deduplication** (same email from multiple sources)  
✅ **Unified format** (standardized across all providers)  
✅ **Flexible querying** (unread, recent, all)  
✅ **JSON export** (for automation/integration)

## Next Steps

### Phase 2: Auto-Drafting (Week 3-4)

- Sender analysis (detect patterns)
- Response templates
- Draft generation via LLM
- Post to #exec-approvals for review

### Phase 3: Cron Automation (Week 5-6)

- Scheduled fetches (every 2-4 hours)
- Morning brief (6 AM)
- Evening digest (6 PM)
- Urgent sweep (every 30 min)

## Safety

🔒 **Never auto-sends emails or iMessages**  
All response drafts go to #exec-approvals for human review.

### Security Barriers

This system has **multiple layers of protection** against accidental sending:

1. **`lib/send_guard.py`** - Runtime blocker that:
   - Blocks all Composio send actions (GMAIL_SEND_EMAIL, OUTLOOK_SEND_MAIL, etc.)
   - Patches subprocess.run/os.system to block AppleScript sends
   - Raises `SendBlockedError` if any send operation is attempted

2. **Read-only database access** for iMessages (`?mode=ro`)

3. **No send endpoints** in the web API

4. **All drafts reviewed via Slack** before manual sending

See **SECURITY.md** for full details.

## Dependencies

- Python 3.7+
- Composio API key (set as `COMPOSIO_API_KEY`)
- Connected accounts (Gmail, Outlook, Instantly)

## LLM Configuration

**⚠️ IMPORTANT:** This project does NOT need a separate LLM API key.

All LLM operations (drafting, analysis, etc.) run through **Clawdbot's global Claude Max account**. Do not:
- Set up a separate Anthropic API key
- Configure OpenRouter or other LLM providers
- Add LLM-related environment variables

Clawdbot handles all AI inference directly through its existing Claude Max subscription.

## Troubleshooting

### No emails fetched

- Check `COMPOSIO_API_KEY` is set
- Verify connected accounts: `composio integrations`
- Check account status (ACTIVE vs EXPIRED)

### Outlook/Instantly failing

- Verify account IDs in `config/accounts.json`
- Check Composio integration status
- Re-authorize expired accounts

### Priority scores seem wrong

- Customize VIP senders in `lib/priority_scorer.py`
- Adjust scoring weights if needed
- Add custom keywords for your workflow

## License

Internal project - not for external distribution.

---

**Status:** ✅ Phase 1 Complete (API setup + unified fetching)  
**Next:** Phase 2 (Auto-drafting + sender analysis)
