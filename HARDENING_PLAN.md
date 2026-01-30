# Email Automation Hardening Plan
**Created:** 2026-01-30
**Model:** Claude Opus 4
**Status:** Planning → Implementation

---

## 🎯 Implementation Order (Priority-First)

### **CRITICAL PATH** (Do First - Required for Production)

#### 1. Error Handling & Resilience ⚡ HIGH PRIORITY
**Why Critical:** APIs will fail. System must be resilient.

**Implementation:**
- Add retry logic with exponential backoff to all API calls
- Graceful degradation (skip email if draft fails, continue processing)
- Structured error logging to `logs/email-automation.log`
- Alert mechanism for repeated failures
- Timeout handling for Claude/Composio calls

**Files to modify:**
- `lib/email_fetcher.py` - Add retries to Composio calls
- `lib/draft_generator.py` - Add retries to Claude calls
- `scripts/auto_draft.py` - Add error recovery
- `scripts/sync_emails.py` - Add error recovery
- Create `lib/retry_utils.py` - Shared retry logic

**Success criteria:**
- ✅ API failure doesn't crash script
- ✅ Errors logged with context
- ✅ Retries happen automatically (3 attempts, exponential backoff)
- ✅ User notified only after all retries fail

---

#### 2. Rate Limiting & API Protection ⚡ HIGH PRIORITY
**Why Critical:** Prevent API hammering, manage costs, avoid rate limits.

**Implementation:**
- Max 10 drafts per run
- 2-second delay between Claude Opus calls
- Track API usage in database
- Skip if draft generated in last 30 minutes for same sender
- Daily/hourly usage caps

**Files to create:**
- `lib/rate_limiter.py` - Rate limiting logic
- `database/migrations/003_add_rate_limiting.sql`

**Database changes:**
```sql
CREATE TABLE api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service TEXT NOT NULL, -- 'composio' or 'claude'
  action TEXT NOT NULL, -- 'fetch_emails', 'generate_draft'
  timestamp TEXT NOT NULL,
  tokens_used INTEGER,
  cost_usd REAL,
  success INTEGER DEFAULT 1
);

CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_api_usage_service ON api_usage(service);
```

**Files to modify:**
- `scripts/auto_draft.py` - Enforce limits
- `lib/draft_generator.py` - Track usage

**Success criteria:**
- ✅ Never exceeds 10 drafts per run
- ✅ Delays between API calls respected
- ✅ Duplicate drafts prevented (30-min window)
- ✅ Usage tracked in database

---

#### 3. Sender Whitelist/Blacklist ⚡ HIGH PRIORITY
**Why Critical:** Don't waste API calls on newsletters/spam.

**Implementation:**
- Config-driven whitelist/blacklist
- Pattern matching (wildcards, domains)
- Relationship-type based filtering
- Override mechanism for urgent emails

**Files to create:**
- `config/sender_filters.json` - Filter configuration

**Config structure:**
```json
{
  "skip_drafting": {
    "emails": [
      "no-reply@*",
      "noreply@*",
      "newsletter@*",
      "notifications@*",
      "donotreply@*"
    ],
    "domains": [
      "mailchimp.com",
      "sendgrid.net",
      "klaviyo.com"
    ],
    "relationship_types": [
      "automated",
      "newsletter"
    ]
  },
  "always_draft": {
    "emails": [
      "*@anthropic.com",
      "*@stripe.com",
      "*@clawdbot.com"
    ],
    "domains": [],
    "priority_threshold": 90
  }
}
```

**Files to modify:**
- `scripts/auto_draft.py` - Apply filters
- `lib/sender_analyzer.py` - Check filters

**Success criteria:**
- ✅ No drafts for no-reply emails
- ✅ No drafts for newsletters
- ✅ VIP senders always get drafts
- ✅ Easy to update filters without code changes

---

#### 4. Draft Approval Workflow ⚡ HIGH PRIORITY
**Why Critical:** Need to track what happens to drafts after generation.

**Database changes:**
```sql
ALTER TABLE draft_responses ADD COLUMN approved_at TEXT;
ALTER TABLE draft_responses ADD COLUMN approved_by TEXT;
ALTER TABLE draft_responses ADD COLUMN rejected_at TEXT;
ALTER TABLE draft_responses ADD COLUMN rejected_by TEXT;
ALTER TABLE draft_responses ADD COLUMN rejection_reason TEXT;
ALTER TABLE draft_responses ADD COLUMN edited_text TEXT; -- If user modified draft
ALTER TABLE draft_responses ADD COLUMN sent_at TEXT; -- When user actually sent email
ALTER TABLE draft_responses ADD COLUMN sent_via TEXT; -- 'manual', 'gmail_ui', etc.
ALTER TABLE draft_responses ADD COLUMN feedback_score INTEGER; -- 1-5 rating
ALTER TABLE draft_responses ADD COLUMN feedback_notes TEXT;
```

**Files to create:**
- `database/migrations/004_add_approval_workflow.sql`
- `scripts/approve_draft.py` - CLI tool to approve
- `scripts/reject_draft.py` - CLI tool to reject

**Files to modify:**
- `lib/database.py` - Add approval methods

**Success criteria:**
- ✅ Can mark draft as approved
- ✅ Can mark draft as rejected with reason
- ✅ Can track edits made to draft
- ✅ Can track when/how email was sent
- ✅ Can rate draft quality for learning

---

### **HIGH VALUE** (Significant Improvement)

#### 5. Web Dashboard Enhancements 🎨 MEDIUM PRIORITY
**Why Important:** Better UX for reviewing/managing emails and drafts.

**New pages to build:**
```
/dashboard - Triage queue (urgent emails, sorted by priority)
/drafts - All generated drafts (tabs: pending/approved/rejected/sent)
/senders - Sender profiles & history
/settings - Configure filters, priorities, API keys
/analytics - Usage stats, draft acceptance rate
```

**Components to build:**
- Email card (priority badge, sender info, preview)
- Draft preview (side-by-side with original)
- Inline editor for drafts
- Approval buttons (Approve/Reject/Edit/Regenerate)
- Sender profile card

**Files to create:**
- `web/app/dashboard/page.tsx`
- `web/app/drafts/page.tsx`
- `web/app/senders/page.tsx`
- `web/app/settings/page.tsx`
- `web/app/analytics/page.tsx`
- `web/components/EmailCard.tsx`
- `web/components/DraftEditor.tsx`
- `web/components/SenderProfile.tsx`

**API routes to create:**
- `web/app/api/drafts/[id]/approve/route.ts`
- `web/app/api/drafts/[id]/reject/route.ts`
- `web/app/api/drafts/[id]/edit/route.ts`
- `web/app/api/drafts/[id]/regenerate/route.ts`
- `web/app/api/senders/route.ts`
- `web/app/api/senders/[email]/route.ts`

**Success criteria:**
- ✅ Can view all urgent emails in dashboard
- ✅ Can approve/reject drafts from UI
- ✅ Can edit drafts inline
- ✅ Can view sender history
- ✅ Can configure filters from UI

---

#### 6. Email Threading 🎨 MEDIUM PRIORITY
**Why Important:** Group related emails together, better context.

**Database schema:**
```sql
CREATE TABLE email_threads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id TEXT UNIQUE NOT NULL,
  subject TEXT,
  participants TEXT, -- JSON array of email addresses
  email_count INTEGER DEFAULT 0,
  last_email_at TEXT,
  first_email_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_threads_thread_id ON email_threads(thread_id);
CREATE INDEX idx_threads_last_email ON email_threads(last_email_at);

-- Link emails to threads
ALTER TABLE emails ADD COLUMN thread_id TEXT;
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
```

**Files to create:**
- `database/migrations/005_add_threading.sql`
- `lib/thread_analyzer.py` - Extract/analyze threads

**Files to modify:**
- `lib/email_normalizer.py` - Extract thread_id from headers
- `lib/database.py` - Add thread methods

**Success criteria:**
- ✅ Emails grouped by thread
- ✅ Thread participant list maintained
- ✅ Can view conversation history
- ✅ Draft context includes full thread

---

#### 7. Smart Filters & Categorization 💡 MEDIUM PRIORITY
**Why Important:** Auto-categorize for better organization.

**Categories:**
```python
CATEGORIES = {
  'financial': ['invoice', 'payment', 'receipt', 'billing'],
  'support': ['ticket', 'support', 'help', 'issue'],
  'partnership': ['partnership', 'collaboration', 'opportunity'],
  'newsletter': ['unsubscribe', 'newsletter', 'digest'],
  'action_required': ['action required', 'urgent', 'deadline', 'asap'],
  'security': ['security alert', 'password', 'verification', 'suspicious'],
  'social': ['liked', 'commented', 'mentioned', 'followed']
}
```

**Database changes:**
```sql
ALTER TABLE emails ADD COLUMN category TEXT;
CREATE INDEX idx_emails_category ON emails(category);
```

**Files to create:**
- `lib/categorizer.py` - Auto-categorization logic
- `database/migrations/006_add_categories.sql`

**Success criteria:**
- ✅ Emails auto-categorized on sync
- ✅ Can filter by category in UI
- ✅ Categories visible in dashboard

---

### **NICE TO HAVE** (Polish & Analytics)

#### 8. Analytics Dashboard 📊 LOW PRIORITY
**Why Nice:** Track system performance, draft quality.

**Metrics to track:**
- Drafts generated per day/week
- Average response time to urgent emails
- Most common senders
- Draft acceptance rate (approved vs rejected)
- Token usage & cost tracking
- Email volume by category
- Peak email hours

**Files to create:**
- `web/app/analytics/page.tsx`
- `web/app/api/analytics/route.ts`
- `lib/analytics.py` - Query helpers

**Success criteria:**
- ✅ Visual charts for key metrics
- ✅ Date range filters
- ✅ Export to CSV

---

#### 9. Draft Preview & Edit (Enhanced) 💡 LOW PRIORITY
**Why Nice:** Better draft editing experience.

**Features:**
- Side-by-side view (original email + draft)
- Syntax highlighting for draft
- Version history (if regenerated multiple times)
- Suggested edits (highlight what changed)
- One-click copy to clipboard
- Email preview rendering

**Files to create:**
- `web/components/DraftEditor.tsx` - Enhanced editor
- `web/components/EmailPreview.tsx` - Render email HTML

**Success criteria:**
- ✅ Easy to compare original vs draft
- ✅ Can edit draft inline
- ✅ Can see version history
- ✅ Can copy draft to clipboard

---

#### 10. Batch Operations 🛠️ LOW PRIORITY
**Why Nice:** Cleanup & maintenance tasks.

**Operations:**
```bash
# Archive old emails
python3 scripts/batch_archive.py --older-than 30d

# Bulk mark as read
python3 scripts/bulk_mark_read.py --from "newsletter@*"

# Delete old drafts
python3 scripts/cleanup_drafts.py --status rejected --older-than 7d

# Recalculate priority scores
python3 scripts/recalculate_priorities.py --all

# Regenerate sender profiles
python3 scripts/rebuild_sender_profiles.py
```

**Files to create:**
- `scripts/batch_archive.py`
- `scripts/bulk_mark_read.py`
- `scripts/cleanup_drafts.py`
- `scripts/recalculate_priorities.py`
- `scripts/rebuild_sender_profiles.py`

**Success criteria:**
- ✅ Can bulk operations via CLI
- ✅ Dry-run mode for safety
- ✅ Progress indicators

---

## 📋 Implementation Checklist

### Phase 1: Critical Hardening (Week 1)
- [ ] 1. Error Handling & Resilience
- [ ] 2. Rate Limiting & API Protection
- [ ] 3. Sender Whitelist/Blacklist
- [ ] 4. Draft Approval Workflow

### Phase 2: High-Value Features (Week 2)
- [ ] 5. Web Dashboard Enhancements
- [ ] 6. Email Threading
- [ ] 7. Smart Filters & Categorization

### Phase 3: Polish & Analytics (Week 3)
- [ ] 8. Analytics Dashboard
- [ ] 9. Draft Preview & Edit (Enhanced)
- [ ] 10. Batch Operations

---

## 🚀 Execution Plan

**Order of implementation:**
1. ✅ Error handling (foundation)
2. ✅ Rate limiting (cost control)
3. ✅ Sender filters (waste reduction)
4. ✅ Approval workflow (tracking)
5. ✅ Web dashboard (UX)
6. ✅ Email threading (context)
7. ✅ Smart filters (organization)
8. ✅ Analytics (insights)
9. ✅ Enhanced editing (polish)
10. ✅ Batch operations (maintenance)

**Each implementation will:**
1. Create/modify files
2. Add database migrations if needed
3. Write tests
4. Update documentation
5. Commit to git

---

**Ready to execute!** Starting with #1: Error Handling & Resilience.
