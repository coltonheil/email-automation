#!/usr/bin/env python3
"""
Draft Generator
Uses Claude to generate contextual email response drafts
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class DraftGenerator:
    """Generates email draft responses using Claude"""
    
    def __init__(self, anthropic_api_key: str = None):
        """
        Initialize draft generator
        
        Args:
            anthropic_api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
        """
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")
        
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-sonnet-4"  # Latest model
    
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
        
        # Call Claude API
        response = self._call_claude_api(prompt)
        
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
    
    def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call Claude API to generate response
        
        Args:
            prompt: Full prompt for Claude
            
        Returns:
            API response dict
        """
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        
        payload = {
            'model': self.model,
            'max_tokens': 1024,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,  # Slightly creative but focused
        }
        
        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Claude API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Failed to call Claude API: {str(e)}")
