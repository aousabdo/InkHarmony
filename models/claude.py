"""
Claude API integration for InkHarmony.
Handles communication with Anthropic's Claude models.
"""
import logging
import time
import json
import sys
import os
from typing import Dict, List, Any, Optional, Generator, Tuple, Union
from dataclasses import dataclass, asdict

# Add the project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, DEFAULT_CLAUDE_MODEL

# Set up logging
logger = logging.getLogger(__name__)

class ClaudeAPIError(Exception):
    """Exception raised for Claude API errors."""
    pass


@dataclass
class ClaudeMessage:
    """Structured message for Claude API."""
    role: str
    content: str


@dataclass
class CompletionOptions:
    """Options for Claude API completion."""
    model: str = DEFAULT_CLAUDE_MODEL
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 0
    stop_sequences: Optional[List[str]] = None
    system: Optional[str] = None
    stream: bool = False


class ClaudeAPI:
    """Interface to Anthropic's Claude API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Claude API client.
        
        Args:
            api_key: Anthropic API key (default: from config)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
            
        self.client = Anthropic(api_key=self.api_key)
    
    def complete(self, messages: List[ClaudeMessage], options: CompletionOptions = None) -> str:
        """
        Generate a completion from Claude.
        
        Args:
            messages: List of conversation messages
            options: Completion options
            
        Returns:
            Generated text response
        
        Raises:
            ClaudeAPIError: If the API call fails
        """
        if options is None:
            options = CompletionOptions()
            
        # Convert messages to Claude format
        claude_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        try:
            response = self.client.messages.create(
                model=options.model,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p if options.top_p is not None else None,
                top_k=options.top_k if options.top_k is not None else None,
                system=options.system,
                messages=claude_messages,
                stream=False
            )
            
            return response.content[0].text
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise ClaudeAPIError(f"Claude API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise ClaudeAPIError(f"Unexpected error: {str(e)}")
    
    def stream_complete(self, messages: List[ClaudeMessage], 
                       options: CompletionOptions = None) -> Generator[str, None, None]:
        """
        Stream a completion from Claude.
        
        Args:
            messages: List of conversation messages
            options: Completion options
            
        Yields:
            Text chunks as they are generated
        
        Raises:
            ClaudeAPIError: If the API call fails
        """
        if options is None:
            options = CompletionOptions(stream=True)
        else:
            options.stream = True
            
        # Convert messages to Claude format
        claude_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        try:
            with self.client.messages.stream(
                model=options.model,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p if options.top_p is not None else None,
                top_k=options.top_k if options.top_k is not None else None,
                system=options.system,
                messages=claude_messages
            ) as stream:
                for chunk in stream:
                    if chunk.type == "content_block_delta" and chunk.delta.type == "text":
                        yield chunk.delta.text
                        
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise ClaudeAPIError(f"Claude API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise ClaudeAPIError(f"Unexpected error: {str(e)}")
    
    def complete_with_retry(self, messages: List[ClaudeMessage], options: CompletionOptions = None,
                           max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        Generate a completion with retry logic.
        
        Args:
            messages: List of conversation messages
            options: Completion options
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries (with exponential backoff)
            
        Returns:
            Generated text response
        
        Raises:
            ClaudeAPIError: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                return self.complete(messages, options)
            except ClaudeAPIError as e:
                logger.warning(f"Retry {attempt + 1}/{max_retries}: {str(e)}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    # Last attempt failed
                    raise
    
    def user_message(self, content: str) -> ClaudeMessage:
        """
        Create a user message.
        
        Args:
            content: Message content
            
        Returns:
            ClaudeMessage with user role
        """
        return ClaudeMessage(role="user", content=content)
    
    def assistant_message(self, content: str) -> ClaudeMessage:
        """
        Create an assistant message.
        
        Args:
            content: Message content
            
        Returns:
            ClaudeMessage with assistant role
        """
        return ClaudeMessage(role="assistant", content=content)
    
    def build_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Build a prompt from a template and variables.
        
        Args:
            template: Prompt template with {variable} placeholders
            variables: Dictionary of variables to substitute
            
        Returns:
            Formatted prompt
        """
        return template.format(**variables)
    
    def build_structured_prompt(self, sections: Dict[str, Any]) -> str:
        """
        Build a structured prompt from sections.
        
        Args:
            sections: Dictionary mapping section names to content
            
        Returns:
            Formatted structured prompt
        """
        parts = []
        for section, content in sections.items():
            parts.append(f"# {section}")
            parts.append(content)
            parts.append("")  # Empty line
            
        return "\n".join(parts)


# Global Claude API instance - initialize lazily when needed
def get_claude_api():
    """Get or create a ClaudeAPI instance only when needed and if the API key is available."""
    if not ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key available. Claude AI functionality will not work.")
        return None
        
    try:
        return ClaudeAPI()
    except ValueError as e:
        logger.warning(f"Failed to initialize ClaudeAPI: {str(e)}")
        return None

# Replace direct global instance with None initially
claude_api = None