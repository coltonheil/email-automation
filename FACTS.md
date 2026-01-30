# Email Automation - Facts

**Last Verified:** 2026-01-30

## Project Type
Multi-inbox email automation system (triage, routing, drafting)

## Hosting & Infrastructure
- **Type:** Clawdbot service (runs via cron)
- **Location:** `~/clawd/projects/email-automation/`
- **Dependencies:** Composio API, Python 3.7+
- **Verification Source:** `cmd:cd ~/clawd/projects/email-automation && python3 scripts/fetch_all_emails.py --mode unread --limit 5`

## Key Invariants

### 1. Never Auto-Send ⚠️
**All response drafts MUST go to #exec-approvals for human review.**
- No exceptions
- Auto-send is forbidden (safety critical)
- Drafts require explicit approval before sending

### 2. Privacy & Security
- Email content never logged in public channels
- API tokens stored in `~/clawd/.env`
- Composio API key: `COMPOSIO_API_KEY`
- PII handling follows workspace security policy

### 3. Multi-Inbox Architecture
- **8 inboxes total** (1 Gmail + 3 Outlook + 1 Instantly workspace)
- Unified normalization layer (`lib/email_normalizer.py`)
- Single triage queue output
- Deduplication by subject+sender+timestamp

### 4. Priority Scoring System
- Range: 0-100
- **Urgent:** 80-100 (VIP, action required, payments)
- **Normal:** 40-79 (standard emails)
- **Low:** 0-39 (newsletters, marketing, old)
- Scoring logic: `lib/priority_scorer.py`

### 5. Cron Schedule (Target for Phase 3)
- Support/business: every 2 hours
- Personal: every 4 hours
- Instantly: every 2 hours
- Urgent sweep: every 30 min
- Morning brief: 6 AM daily
- Evening digest: 6 PM daily

## API Access

### Gmail (1 account)
- **Method:** Composio
- **Status:** ✅ Connected
- **Account ID:** `481bf3fb-1b5d-4dac-9395-c97ead2a404a`
- **Action:** `GMAIL_FETCH_EMAILS`
- **Credentials:** `COMPOSIO_API_KEY` in `.env`

### Outlook (3 accounts)
- **Method:** Composio
- **Status:** ✅ Connected
- **Account IDs:** 
  - `4f48e4cd-2250-4018-8abc-ff633f144967`
  - `e662c7fe-fb04-44c3-84e0-25275d1a313f`
  - `cabb6ded-a951-4447-8149-d2f58ae9f14f`
- **Action:** `OUTLOOK_OUTLOOK_LIST_MESSAGES`
- **Credentials:** `COMPOSIO_API_KEY` in `.env`

### Instantly (1 workspace, 4 sending accounts)
- **Method:** Composio
- **Status:** ✅ Connected
- **Account ID:** `03304007-f97f-42a6-be6b-03eb15e8c0c0`
- **Action:** `INSTANTLY_LIST_EMAILS` (TBD - may need different action)
- **Credentials:** `COMPOSIO_API_KEY` in `.env`
- **Note:** Instantly integration exists, but specific actions may vary

## Known Constraints

- Composio rate limits: 120 requests/minute (per action)
- Gmail: OAuth token refresh handled automatically by Composio
- Outlook: OAuth token refresh handled automatically by Composio
- Instantly: Workspace contains 4 sending accounts (accessed via single integration)
- HTTP requests must include browser User-Agent to avoid Cloudflare blocking

## Implementation Details

### Email Fetching
- **Script:** `scripts/fetch_all_emails.py`
- **Modes:** `unread`, `recent`, `all`
- **Limit:** Configurable per account (default 50)
- **Output:** JSON or human-readable summary

### Data Normalization
- **Module:** `lib/email_normalizer.py`
- **Standardizes:** subject, from, to, cc, body, timestamps, labels
- **Dedup key:** MD5 of subject+from+rounded_timestamp

### Priority Scoring
- **Module:** `lib/priority_scorer.py`
- **VIP domains:** stripe.com, anthropic.com, openai.com, clawdbot.com
- **VIP keywords:** urgent, asap, important, critical, action required, etc.
- **Customizable:** Edit `VIP_DOMAINS` and `VIP_KEYWORDS` in source

## Configuration

- **Accounts:** `config/accounts.json`
- **Environment:** `~/clawd/.env` (Composio API key)
- **Data output:** `data/` directory (optional JSON export)

## Testing

### Verification Command
```bash
cd ~/clawd/projects/email-automation
export COMPOSIO_API_KEY=$(grep COMPOSIO_API_KEY ~/clawd/.env | cut -d= -f2)
python3 scripts/fetch_all_emails.py --mode unread --limit 5
```

Expected output: Summary of unread emails across all 8 inboxes.

## Related Workstreams

- Design doc: `workstreams/x-content/research/email-automation-design.md`
- Integration scan: `workstreams/_GLOBAL/INTEGRATIONS.json`
- Slack channel: `#repo-email-automation`

## Decisions

- **2026-01-30:** Removed @info shared mailbox from scope (user to handle via Replit forwarding)
- **2026-01-30:** Total inbox count: 8 (not 9)
- **2026-01-30:** Phase 1 complete - all providers connected and tested
- **2026-01-27:** Project initiated, design doc created

## Top Invariants

1. **Never auto-send emails** - all drafts require approval
2. **8 inboxes total** - 1 Gmail + 3 Outlook + 1 Instantly workspace
3. **Priority scoring 0-100** - Urgent (80+), Normal (40-79), Low (<40)
4. **Composio API** - single integration point for all providers
5. **Browser User-Agent required** - to avoid Cloudflare blocking
