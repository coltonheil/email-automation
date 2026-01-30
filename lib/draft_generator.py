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
        
        # Extract current email details
        current_email = sender_context['current_email']
        email_subject = current_email.get('subject', '(no subject)')
        email_body = current_email.get('body', current_email.get('snippet', ''))
        
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
    
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=3.0,
        exceptions=(subprocess.TimeoutExpired, subprocess.CalledProcessError, ConnectionError)
    )
    def _call_claude_via_clawdbot(self, prompt: str) -> Dict[str, Any]:
        """
        Call Claude via Clawdbot (uses your Claude Max subscription)
        With automatic retry on failure
        
        Args:
            prompt: Full prompt for Claude
            
        Returns:
            Response dict with text and metadata
            
        Raises:
            Exception: On permanent failure after all retries
        """
        logger.info(f"Calling Claude Opus via Clawdbot (session: {self.session_label})")
        
        try:
            # Build clawdbot command to send message via sessions_send
            # This leverages your existing Claude Max subscription
            cmd = [
                'clawdbot',
                'sessions_send',
                '--label', self.session_label,
                '--model', self.model,
                '--timeout', '60',
                '--message', prompt
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Extra buffer for network + processing
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"Clawdbot command failed: {error_msg}")
                raise Exception(f"Clawdbot error: {error_msg}")
            
            # Parse response (Clawdbot returns plain text response)
            response_text = result.stdout.strip()
            
            if not response_text:
                logger.error("Claude returned empty response")
                raise Exception("Empty response from Claude")
            
            logger.info(f"Claude draft generated successfully ({len(response_text)} chars)")
            
            # Return in API-like format
            return {
                'content': [{'text': response_text}],
                'usage': {
                    'input_tokens': 0,  # Clawdbot doesn't expose these
                    'output_tokens': 0
                }
            }
        
        except subprocess.TimeoutExpired:
            logger.error("Claude request timed out after 90 seconds")
            raise Exception("Claude request timed out after 90 seconds")
        except Exception as e:
            logger.error(f"Failed to call Claude via Clawdbot: {str(e)}")
            raise Exception(f"Failed to call Claude via Clawdbot: {str(e)}")
