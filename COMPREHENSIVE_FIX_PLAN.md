# Comprehensive Fix Plan - Context Overflow & API Errors

**Date:** 2026-01-30
**Model:** Claude Opus 4
**Issues Identified:**

1. ✅ HTTP 413 "Payload Too Large" from Composio Gmail API
2. ✅ Context overflow when generating drafts with large email bodies
3. ✅ sessions_send command error in draft generator
4. ⚠️ Outlook emails with massive HTML bodies (potential 500KB+)

---

## Root Cause Analysis

### Issue 1: Gmail 413 Payload Error

**Problem:**
- Composio GMAIL_FETCH_EMAILS returns 413 when response is too large
- Current limit: `max_results: min(limit, 20)`
- Even 20 emails can exceed payload limits if they have large bodies

**Fix:**
- Reduce max_results to 10
- Use `include_payload: False` to fetch metadata only
- Fetch full body separately only when needed

### Issue 2: Context Overflow in Draft Generation

**Problem:**
- Outlook emails can have 500KB+ HTML bodies
- Current truncation: 4000 chars (not enough for worst cases)
- Sender history can include multiple large emails
- Combined context exceeds Claude's input token limit (~200K tokens = ~600K chars)

**Fix:**
- **Aggressive truncation:** Limit email body to 2000 chars (not 4000)
- **Strip sender history bodies:** Only keep subjects + snippets (no full bodies)
- **Limit history:** Max 10 emails (not 20)
- **Remove raw_data:** Don't include full raw email objects in context

### Issue 3: sessions_send Command Error

**Problem:**
- draft_generator.py tries to call Clawdbot via `clawdbot sessions_send`
- This command doesn't exist in the CLI
- Should use direct Anthropic API instead

**Fix:**
- **Primary:** Use ANTHROPIC_API_KEY for direct API calls
- **Fallback:** Remove Clawdbot integration attempt
- **Update docs:** Clarify that ANTHROPIC_API_KEY is required

### Issue 4: Outlook HTML Email Bodies

**Problem:**
- Microsoft Graph API returns full HTML body by default
- Can be 100KB-500KB of inline styles, tracking pixels, etc.
- HTML stripping helps but not enough

**Fix:**
- Fetch only `bodyPreview` (256 char summary) from Outlook API
- Don't fetch full `body.content` unless absolutely necessary
- Add $select parameter to Outlook API calls

---

## Implementation Plan

### Phase 1: Immediate Fixes (Critical)

**1. Email Fetcher (lib/email_fetcher.py)**
- ✅ Reduce Gmail max_results to 10
- ✅ Add $select to Outlook to exclude body content
- ✅ Fetch bodyPreview only

**2. Email Normalizer (lib/email_normalizer.py)**
- ✅ Truncate all bodies to 2000 chars max
- ✅ Prefer snippet/preview over full body
- ✅ Remove raw_data from normalized output

**3. Sender Analyzer (lib/sender_analyzer.py)**
- ✅ Limit history to 10 emails (not 20)
- ✅ Strip email bodies from history (keep subject + snippet only)
- ✅ Reduce current_email body to 1500 chars

**4. Draft Generator (lib/draft_generator.py)**
- ✅ Remove Clawdbot sessions_send attempt
- ✅ Use direct Anthropic API only
- ✅ Add better error messages for missing API key
- ✅ Reduce max_chars in clean_email_body to 1500

### Phase 2: Enhanced Safeguards

**1. Add Context Size Monitor**
- Calculate total context size before sending to Claude
- Warn if approaching 100K chars
- Auto-truncate if needed

**2. Progressive Truncation**
- Level 1: 2000 chars per email body
- Level 2: 1500 chars if context > 50K
- Level 3: 1000 chars if context > 80K
- Emergency: 500 chars if context > 100K

**3. Smarter Body Extraction**
- Prefer plain text over HTML
- Extract first N paragraphs only
- Skip signature blocks, disclaimers, footers
- Remove quoted replies

### Phase 3: Long-term Improvements

**1. Separate Body Storage**
- Store full email body in database
- Include only snippet in context
- Fetch full body only if draft generator needs it

**2. Intelligent Summarization**
- Use Claude to summarize long email threads
- Cache summaries for reuse
- Include summary instead of full text

**3. Better Error Handling**
- Graceful degradation when body is too large
- Fallback to snippet-only mode
- Log truncation events for debugging

---

## Success Criteria

✅ No 413 payload errors from Composio
✅ No context overflow errors from Claude
✅ Drafts generate successfully for Outlook emails
✅ All email fetching works reliably
✅ Context size stays under 50K chars (ideal) or 100K chars (max)

---

## Testing Plan

1. **Fetch Outlook emails** with large HTML bodies
2. **Generate draft** for each one
3. **Monitor context size** in logs
4. **Verify truncation** is working correctly
5. **Check draft quality** (ensure no info loss)

---

## Implementation Timeline

- **Phase 1:** 15 minutes (immediate fixes)
- **Phase 2:** 30 minutes (safeguards)
- **Phase 3:** Future sprint (long-term)

**Start now with Phase 1 fixes.**
