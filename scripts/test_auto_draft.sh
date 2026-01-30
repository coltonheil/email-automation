#!/bin/bash
# Test auto-draft system end-to-end

set -e

echo "🧪 Testing Auto-Draft System"
echo "=============================="
echo

# Check environment
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo "Export it first: export ANTHROPIC_API_KEY=<your-key>"
    exit 1
fi

if [ -z "$COMPOSIO_API_KEY" ]; then
    echo "❌ Error: COMPOSIO_API_KEY not set"
    echo "Export it from .env:"
    export COMPOSIO_API_KEY=$(grep COMPOSIO_API_KEY ~/clawd/.env | cut -d= -f2)
fi

echo "✅ Environment variables set"
echo

# Step 1: Sync some emails
echo "📧 Step 1: Syncing emails..."
cd ~/clawd/projects/email-automation
python3 scripts/sync_emails.py --mode unread --limit 5
echo

# Step 2: Check for urgent emails
echo "🔍 Step 2: Checking for urgent emails..."
URGENT_COUNT=$(sqlite3 database/emails.db "SELECT COUNT(*) FROM emails WHERE is_unread = 1 AND priority_score >= 80;")
echo "Found $URGENT_COUNT urgent unread emails"
echo

# Step 3: Dry run auto-draft
echo "📝 Step 3: Testing auto-draft (dry run)..."
python3 scripts/auto_draft.py --min-priority 80 --limit 2 --dry-run
echo

# Step 4: Generate actual draft (if urgent emails exist)
if [ "$URGENT_COUNT" -gt 0 ]; then
    echo "✍️  Step 4: Generating actual draft..."
    python3 scripts/auto_draft.py --min-priority 80 --limit 1
    echo
    
    # Step 5: Check draft in database
    echo "📊 Step 5: Verifying draft in database..."
    sqlite3 database/emails.db "SELECT id, email_id, model_used, status, substr(draft_text, 1, 100) as draft_preview FROM draft_responses ORDER BY id DESC LIMIT 1;"
    echo
fi

echo "✅ Auto-draft system test complete!"
echo
echo "Next steps:"
echo "1. Review drafts in database (draft_responses table)"
echo "2. Integrate with Slack notifications"
echo "3. Set up background worker to auto-draft new urgent emails"
