# Email Automation - Facts

**Last Verified:** 2025-01-27

## Project Type
Multi-inbox email automation system (triage, routing, drafting)

## Hosting & Infrastructure
- **Type:** Clawdbot service (runs via cron)
- **Location:** Local agent workspace
- **Dependencies:** Composio, Microsoft Graph API, Instantly V2 API
- **Verification Source:** UNKNOWN (no deployment yet)

## Key Invariants

### 1. Never Auto-Send
**All response drafts MUST go to #exec-approvals for human review.**
- No exceptions
- Auto-send is forbidden (safety critical)

### 2. Privacy & Security
- Email content never logged in public channels
- API tokens stored in Clawdbot secrets
- PII handling follows workspace security policy

### 3. Multi-Inbox Architecture
- 9 inboxes total (1 Gmail + 4 Outlook + 4 Instantly)
- Unified normalization layer
- Single triage queue output

### 4. Priority Scoring System
- Range: 0-100
- Urgent: 80+
- Normal: 40-79
- Low: <40

### 5. Cron Schedule (Non-Negotiable)
- Support/business: every 2 hours
- Personal: every 4 hours
- Instantly: every 2 hours
- Urgent sweep: every 30 min
- Morning brief: 6 AM daily
- Evening digest: 6 PM daily

## API Access

### Gmail
- **Method:** Composio integration
- **Status:** ✅ Connected
- **Credentials:** Already configured

### Outlook (4 inboxes)
- **Method:** Microsoft Graph API
- **Status:** ⏳ Setup pending
- **Credentials:** TBD

### Instantly (4 inboxes)
- **Method:** Instantly V2 API
- **Status:** ⏳ Setup pending
- **Credentials:** TBD
- **Docs:** https://developer.instantly.ai/

## Known Constraints

- Composio doesn't support Outlook yet (must use Graph API directly)
- Instantly rate limits: 120 requests/minute
- Gmail via Composio: OAuth token refresh handled automatically

## Related Workstreams

- Design doc: `workstreams/x-content/research/email-automation-design.md`
- Integration scan: `workstreams/_GLOBAL/INTEGRATIONS.json`
