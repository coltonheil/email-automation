# Email Automation

**Unified multi-inbox management system with intelligent triage and auto-draft responses**

## Overview

Consolidates 9 email inboxes into one intelligent triage queue with priority scoring, smart routing, and context-aware response drafting.

## Inboxes (9 Total)

- **1 Gmail** (via Composio integration)
- **4 Outlook/Office365** (via Microsoft Graph API)
- **4 Instantly** (via Instantly V2 API)

## System Architecture

### 1. Unified Inbox Monitor
- Normalizes all 9 inboxes to single triage queue
- Priority scoring (0-100):
  - VIP detection
  - Urgency keywords
  - Question detection
- Categories: customer, prospect, cold_reply, partner, personal, spam

### 2. Smart Routing
- **Urgent (80+)** → Immediate attention
- **Normal (40-79)** → Batch processing  
- **Low (<40)** → Auto-archive

### 3. Auto-Draft Responses
- Context-aware templates (cold reply vs customer support vs personal)
- Uses thread history + CRM data
- All drafts → #exec-approvals for review (never auto-send)

### 4. Cron Schedule
- Support/business: every 2 hours
- Personal: every 4 hours
- Instantly: every 2 hours
- Urgent sweep: every 30 min
- Morning brief: 6 AM daily
- Evening digest: 6 PM daily

## Implementation Timeline (6 Weeks)

- **Week 1-2:** Foundation (Graph API + Instantly API setup)
- **Week 3:** Multi-inbox monitoring
- **Week 4:** Triage system
- **Week 5:** Response drafting
- **Week 6:** Full automation

## Documentation

Full design doc: `workstreams/x-content/research/email-automation-design.md`

## Status

See `STATUS.md` for current progress and next steps.
