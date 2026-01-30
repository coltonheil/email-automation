# Email Automation System - Usage Guide

**Complete guide to using the email automation system with persistent storage and auto-drafting.**

---

## 🚀 Quick Start

### Prerequisites

1. **Environment Variables:**
   ```bash
   export COMPOSIO_API_KEY=<your-composio-key>
   export ANTHROPIC_API_KEY=<your-anthropic-key>
   ```

2. **Install Dependencies:**
   ```bash
   cd ~/clawd/projects/email-automation
   
   # Python dependencies (already have from setup)
   # No additional Python packages needed
   
   # Node.js dependencies
   cd web
   npm install
   ```

---

## 📧 Email Syncing

### Sync Emails to Database

**Incremental sync (only new emails):**
```bash
python3 scripts/sync_emails.py --mode incremental --limit 20
```

**Fetch all unread:**
```bash
python3 scripts/sync_emails.py --mode unread --limit 50
```

**Recent emails (last 24 hours):**
```bash
python3 scripts/sync_emails.py --mode recent --hours 24 --limit 30
```

**Cleanup old read emails:**
```bash
python3 scripts/sync_emails.py --cleanup
```

**Output:**
```
📧 Syncing Primary Gmail account (gmail)... ✅ 5 emails
📧 Syncing Outlook account 1 (outlook)... ✅ 0 emails
📧 Syncing Outlook account 2 (outlook)... ✅ 0 emails
📧 Syncing Outlook account 3 (outlook)... ✅ 0 emails
📧 Syncing Instantly workspace (instantly)... ✅ 0 emails

✅ Sync complete: 5 fetched, 5 new
📊 Database: 5 unread, 2 urgent
```

---

## ✍️ Auto-Drafting

### Generate Draft Responses

**Dry run (see what would be drafted):**
```bash
python3 scripts/auto_draft.py --min-priority 80 --dry-run
```

**Generate drafts for urgent emails:**
```bash
python3 scripts/auto_draft.py --min-priority 80 --limit 5
```

**Output as JSON:**
```bash
python3 scripts/auto_draft.py --min-priority 80 --json
```

**Example Output:**
```
🔍 Found 2 urgent unread emails
📝 2 need drafts (priority >= 80)

📧 Processing: Payment Failed - Action Required...
   From: billing@stripe.com
   📊 Analyzing sender context...
   ✍️  Generating draft with Claude...
   ✅ Draft created (ID: 1)
   📝 Preview: Thank you for notifying me about the payment...

✅ Auto-draft complete: 2 drafts created
```

---

## 🌐 Web Interface

### Start Dev Server

```bash
cd ~/clawd/projects/email-automation/web
npm run dev
```

**Access at:** http://localhost:3000

### API Endpoints

**Get emails from database (instant load):**
```bash
curl http://localhost:3000/api/emails-db?filter=unread&limit=100
```

**With background sync:**
```bash
curl http://localhost:3000/api/emails-db?filter=all&sync=true
```

**Mark email as read:**
```bash
curl -X POST http://localhost:3000/api/emails-db \
  -H "Content-Type: application/json" \
  -d '{"action": "mark_read", "emailId": "gmail_..."}'
```

---

## 🗄️ Database Queries

### Useful SQL Queries

**See all unread emails:**
```bash
sqlite3 database/emails.db "
  SELECT subject, from_email, priority_score, received_at 
  FROM emails 
  WHERE is_unread = 1 
  ORDER BY priority_score DESC;
"
```

**See urgent emails needing drafts:**
```bash
sqlite3 database/emails.db "
  SELECT * FROM unread_urgent_emails;
"
```

**See generated drafts:**
```bash
sqlite3 database/emails.db "
  SELECT d.id, e.subject, e.from_email, d.status, 
         substr(d.draft_text, 1, 100) as preview
  FROM draft_responses d
  JOIN emails e ON d.email_id = e.id
  ORDER BY d.id DESC;
"
```

**See sender profiles:**
```bash
sqlite3 database/emails.db "
  SELECT email_address, name, total_emails_received, 
         relationship_type, avg_priority_score
  FROM sender_profiles
  ORDER BY total_emails_received DESC;
"
```

---

## 🔄 Typical Workflow

### Daily Use:

1. **Morning sync:**
   ```bash
   python3 scripts/sync_emails.py --mode incremental
   ```

2. **Check for urgent emails needing drafts:**
   ```bash
   python3 scripts/auto_draft.py --min-priority 80
   ```

3. **Open web interface:**
   ```bash
   cd web && npm run dev
   # Visit http://localhost:3000
   ```

4. **Review drafts:**
   - Check database for generated drafts
   - Copy draft text
   - Open email client (Gmail/Outlook)
   - Paste, edit if needed
   - Manually send

5. **Mark as read after sending:**
   - In web interface, click "Mark Read"
   - Or via API: POST /api/emails-db

### Weekly Cleanup:

```bash
python3 scripts/sync_emails.py --cleanup
```

This removes read emails older than 30 days.

---

## 📊 Understanding Priority Scores

**Scoring (0-100):**
- **90-100:** Critical (VIP sender + urgent keywords)
- **80-89:** High (important sender or urgent content)
- **60-79:** Normal (standard business email)
- **40-59:** Low-normal (newsletters, updates)
- **0-39:** Low (marketing, old emails)

**Auto-draft triggers at 80+ by default.**

**Adjust threshold:**
```bash
python3 scripts/auto_draft.py --min-priority 70  # Lower threshold
python3 scripts/auto_draft.py --min-priority 90  # Higher threshold
```

---

## 🧪 Testing

### Full System Test:

```bash
export ANTHROPIC_API_KEY=<your-key>
bash scripts/test_auto_draft.sh
```

This tests:
- ✅ Environment setup
- ✅ Email syncing
- ✅ Urgent email detection
- ✅ Dry-run drafting
- ✅ Actual draft generation
- ✅ Database verification

---

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY not provided"
```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

### "COMPOSIO_API_KEY not provided"
```bash
export COMPOSIO_API_KEY=$(grep COMPOSIO_API_KEY ~/clawd/.env | cut -d= -f2)
```

### "Database file not found"
```bash
# The database auto-creates on first sync
python3 scripts/sync_emails.py --mode unread --limit 5
```

### "No emails syncing"
- Check Composio account status
- Verify API key is valid
- Try with higher limit: `--limit 50`

### "Drafts not generating"
- Ensure emails exist with priority >= 80
- Check ANTHROPIC_API_KEY is valid
- Try dry-run first: `--dry-run`

---

## 📈 Performance Tips

**Fast page loads:**
- Frontend reads from database (<100ms)
- Background sync runs separately
- No waiting for API calls

**Efficient syncing:**
- Use `--mode incremental` for regular syncs
- Only fetches new emails since last sync
- Much faster than full sync

**Draft generation:**
- Processes in batches (use `--limit`)
- Claude API takes ~2-4 seconds per draft
- Run during downtime or in background

---

## 🔒 Safety Reminders

### The System NEVER Sends Emails

**What it does:**
- ✅ Fetches emails (read-only)
- ✅ Stores in database
- ✅ Generates draft responses
- ✅ Shows drafts to you

**What it NEVER does:**
- ❌ Send emails on your behalf
- ❌ Reply to emails automatically
- ❌ Access email send APIs
- ❌ Post publicly without review

**Your workflow:**
1. System generates draft
2. You review draft
3. You manually copy draft
4. You open your email client
5. You paste and edit
6. **YOU click Send**

---

## 📱 Future: Slack Integration

**Coming soon:**
- Drafts posted to #exec-approvals automatically
- Slack notifications when urgent emails arrive
- Copy-to-clipboard button in Slack
- Draft approval workflow

**For now:**
- Check database for drafts
- Manually copy draft text
- Send from your email client

---

## 🎯 Best Practices

1. **Sync regularly:** Run incremental sync every 2-5 minutes
2. **Review drafts:** Never send without reading
3. **Cleanup weekly:** Remove old read emails
4. **Monitor priority:** Adjust threshold as needed
5. **Check context:** Sender profiles improve over time

---

## 📞 Support

**Issues:**
- Check logs in terminal output
- Verify environment variables set
- Test with dry-run first

**Documentation:**
- `PHASE1_COMPLETE.md` - Database details
- `PHASE2_COMPLETE.md` - Auto-draft details
- `README.md` - Project overview

---

**You're all set! Start with a sync, generate some drafts, and enjoy your intelligent email assistant.** 🚀
