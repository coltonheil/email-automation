#!/usr/bin/env python3
"""
Draft Generator
Uses Claude to generate contextual email response drafts via Clawdbot
With robust error handling and retry logic
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional
from retry_utils import retry_with_backoff, logger
try:
    from text_utils import clean_email_body, truncate_text
    from context_monitor import estimate_context_size, progressive_truncate, log_context_stats
except ImportError:
    from .text_utils import clean_email_body, truncate_text
    from .context_monitor import estimate_context_size, progressive_truncate, log_context_stats


class DraftGenerator:
    """Generates email draft responses using Claude via Clawdbot"""
    
    def __init__(self, session_label: str = "email-automation"):
        """
        Initialize draft generator
        
        Args:
            session_label: Clawdbot session label to use (leverages your Claude Max subscription)
        """
        self.session_label = session_label
        self.model = "opus"  # Using Claude Opus 4 via your existing subscription
    
    def generate_draft(
        self, 
        sender_context: Dict[str, Any],
        user_writing_style: str = "professional and concise",
        additional_instructions: str = None
    ) -> Dict[str, Any]:
        """
        Generate a draft email response
        
        Args:
            sender_context: Context from SenderAnalyzer.build_sender_context()
            user_writing_style: User's preferred writing style
            additional_instructions: Extra instructions for the draft
            
        Returns:
            Dict with 'draft_text', 'model_used', 'reasoning' (if applicable)
        """
        # Build prompt
        prompt = self._build_prompt(sender_context, user_writing_style, additional_instructions)
        
        # Call Claude via Clawdbot (uses your Claude Max subscription)
        response = self._call_claude_via_clawdbot(prompt)
        
        # Extract draft
        draft_text = response.get('content', [{}])[0].get('text', '')
        
        return {
            'draft_text': draft_text,
            'model_used': self.model,
            'prompt_tokens': response.get('usage', {}).get('input_tokens', 0),
            'completion_tokens': response.get('usage', {}).get('output_tokens', 0),
        }
    
    def _build_prompt(
        self,
        sender_context: Dict[str, Any],
        user_writing_style: str,
        additional_instructions: str
    ) -> str:
        """Build Claude prompt with sender context"""
        
        # CRITICAL: Check context size and truncate if needed
        log_context_stats(sender_context, logger)
        sender_context = progressive_truncate(sender_context, max_tokens=25000)
        
        # Extract current email details
        current_email = sender_context['current_email']
        email_subject = current_email.get('subject', '(no subject)')
        raw_body = current_email.get('body', current_email.get('snippet', ''))
        
        # CRITICAL: Clean and truncate body to prevent context overflow
        # Email bodies can be 500KB+ of HTML - must limit aggressively
        email_body = clean_email_body(raw_body, max_chars=1500)
        
        # Build context summary
        context_summary = self._format_context_summary(sender_context)
        
        # Build prompt
        prompt_parts = [
            "You are helping draft an email response. You will NEVER send emails directly.",
            "Your role is to generate a draft that the user will review and manually send.",
            "",
            "=== SENDER CONTEXT ===",
            context_summary,
            "",
            "=== EMAIL TO RESPOND TO ===",
            f"Subject: {email_subject}",
            "",
            email_body,
            "",
            "=== YOUR TASK ===",
            f"Draft a {user_writing_style} response that:",
            "1. Addresses the sender's request or question directly",
            "2. Matches the relationship type and writing style noted above",
            "3. Is appropriate for the urgency level",
            "4. Sounds natural and authentic",
            "5. Does NOT include a signature (user will add their own)",
            ""
        ]
        
        if additional_instructions:
            prompt_parts.append(f"Additional instructions: {additional_instructions}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "IMPORTANT GUIDELINES:",
            "- Do NOT include 'Subject:' line (this is a reply)",
            "- Do NOT include signature/sign-off with name (user adds this)",
            "- Keep it brief and actionable",
            "- Match the sender's communication style",
            "- Be helpful and clear",
            "",
            "Generate ONLY the email body text (no metadata, no subject line, no signature):"
        ])
        
        return '\n'.join(prompt_parts)
    
    def _format_context_summary(self, context: Dict[str, Any]) -> str:
        """Format sender context for prompt"""
        parts = []
        
        # Sender info
        sender_name = context.get('sender_name', 'Unknown')
        sender_email = context.get('sender_email', '')
        parts.append(f"Sender: {sender_name} <{sender_email}>")
        
        # Relationship
        rel_type = context.get('relationship_type', 'unknown').replace('_', ' ').title()
        parts.append(f"Relationship: {rel_type}")
        
        # History
        total_emails = context.get('total_emails_received', 0)
        if total_emails > 0:
            parts.append(f"Email history: {total_emails} previous emails")
        
        # Topics
        topics = context.get('common_topics', [])
        if topics:
            topics_str = ', '.join(topics[:5])
            parts.append(f"Common topics: {topics_str}")
        
        # Writing style
        style = context.get('writing_style', 'professional').title()
        parts.append(f"Their writing style: {style}")
        
        # Urgency
        urgency = context.get('urgency_level', 'normal').upper()
        parts.append(f"Urgency level: {urgency}")
        
        return '\n'.join(parts)
    
    def _call_claude_via_clawdbot(self, prompt: str) -> Dict[str, Any]:
        """
        Generate draft using Claude API directly
        
        Uses ANTHROPIC_API_KEY from environment if available,
        otherwise raises an error indicating manual draft generation is needed.
        
        Args:
            prompt: Full prompt for Claude
            
        Returns:
            Response dict with text and metadata
        """
        import urllib.request
        import urllib.error
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            # No API key - drafts must be generated manually via Clawdbot agent
            logger.warning("No ANTHROPIC_API_KEY set. Drafts must be generated via Clawdbot agent.")
            raise Exception(
                "No ANTHROPIC_API_KEY available. "
                "Ask Clawdbot to generate drafts manually, or set ANTHROPIC_API_KEY."
            )
        
        logger.info(f"Calling Claude {self.model} via Anthropic API")
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        
        # Map model alias to full name
        model_name = self.model
        if model_name == 'opus':
            model_name = 'claude-opus-4-0-20250514'
        elif model_name == 'sonnet':
            model_name = 'claude-sonnet-4-0-20250514'
        
        payload = {
            'model': model_name,
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
        }
        
        try:
            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages',
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                response_text = result.get('content', [{}])[0].get('text', '')
                
                if not response_text:
                    raise Exception("Empty response from Claude")
                
                logger.info(f"Draft generated successfully ({len(response_text)} chars)")
                
                return {
                    'content': [{'text': response_text}],
                    'usage': result.get('usage', {})
                }
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Claude API error {e.code}: {error_body}")
            raise Exception(f"Claude API error: {error_body}")
        except Exception as e:
            logger.error(f"Failed to call Claude API: {str(e)}")
            raise
