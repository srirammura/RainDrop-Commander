import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from typing import Optional, Literal
from commander.services.effort_config import (
    get_effort_level,
    get_effort_headers,
    log_effort_usage,
    EFFORT_ENABLED,
    EffortLevel
)

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-opus-4-5-20251101"  # Using Claude Opus 4.5 for best performance

if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Create client with timeout settings
client = Anthropic(
    api_key=API_KEY,
    timeout=60.0,  # 60 second timeout for individual API calls
    max_retries=2  # Retry up to 2 times on failure
)


def generate_text(
    prompt: str, 
    temperature: float = 0.7, 
    max_tokens: int = 2048,
    task_type: str = "reasoning",
    effort: Optional[EffortLevel] = None
) -> str:
    """
    Generate text using Anthropic Claude API with effort parameter support.
    
    Args:
        prompt: The prompt to send to Claude
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        task_type: Type of task for effort level determination ("validation", "generation", "reasoning", etc.)
        effort: Optional explicit effort level override ("low", "medium", "high")
    
    Returns:
        Generated text string
    """
    try:
        # Determine effort level
        effort_level = effort if effort else get_effort_level(task_type)
        effort_headers = get_effort_headers(effort_level)
        log_effort_usage(effort_level, task_type)
        
        # Prepare request parameters
        request_params = {
            "model": MODEL_NAME,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "timeout": 60.0,  # 60 second timeout for this specific call
        }
        
        # Add effort headers if enabled
        if effort_headers:
            request_params["extra_headers"] = effort_headers
        
        # Make API call with fallback if effort not supported
        try:
            response = client.messages.create(**request_params)
        except Exception as effort_error:
            # If effort parameter causes error, retry without it
            error_str = str(effort_error).lower()
            if "effort" in error_str or "header" in error_str or "400" in error_str:
                print(f"WARNING: Effort parameter not supported, falling back to default behavior")
                log_effort_usage("fallback", task_type)
                # Retry without effort headers
                request_params.pop("extra_headers", None)
                response = client.messages.create(**request_params)
            else:
                raise
        
        if not response.content or len(response.content) == 0:
            raise Exception("Response blocked: No content returned.")
        
        # Claude returns content as a list of text blocks
        text_content = response.content[0]
        if hasattr(text_content, 'text'):
            return text_content.text
        elif isinstance(text_content, str):
            return text_content
        else:
            raise Exception(f"Unexpected content type: {type(text_content)}")
            
    except Exception as error:
        raise Exception(f"Failed to generate text: {str(error)}")


def generate_json(
    prompt: str, 
    temperature: float = 0.3,
    task_type: str = "analysis",
    effort: Optional[EffortLevel] = None
) -> dict:
    """
    Generate JSON response using Anthropic Claude API with effort parameter support.
    
    Args:
        prompt: The prompt to send to Claude
        temperature: Sampling temperature (0.0-1.0)
        task_type: Type of task for effort level determination ("validation", "generation", "synthesis", etc.)
        effort: Optional explicit effort level override ("low", "medium", "high")
    
    Returns:
        Parsed JSON dictionary
    """
    try:
        # Determine effort level
        effort_level = effort if effort else get_effort_level(task_type)
        effort_headers = get_effort_headers(effort_level)
        log_effort_usage(effort_level, task_type)
        
        # Add instruction to return JSON
        json_prompt = prompt + "\n\nReturn only valid JSON, no other text."
        
        # Prepare request parameters
        request_params = {
            "model": MODEL_NAME,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": json_prompt}
            ],
            "timeout": 60.0,  # 60 second timeout for this specific call
        }
        
        # Add effort headers if enabled
        if effort_headers:
            request_params["extra_headers"] = effort_headers
        
        # Make API call with fallback if effort not supported
        try:
            response = client.messages.create(**request_params)
        except Exception as effort_error:
            # If effort parameter causes error, retry without it
            error_str = str(effort_error).lower()
            if "effort" in error_str or "header" in error_str or "400" in error_str:
                print(f"WARNING: Effort parameter not supported, falling back to default behavior")
                log_effort_usage("fallback", task_type)
                # Retry without effort headers
                request_params.pop("extra_headers", None)
                response = client.messages.create(**request_params)
            else:
                raise
        
        if not response.content or len(response.content) == 0:
            raise Exception("Response blocked: No content returned.")
        
        # Claude returns content as a list of text blocks
        text_content = response.content[0]
        if hasattr(text_content, 'text'):
            text = text_content.text
        elif isinstance(text_content, str):
            text = text_content
        else:
            raise Exception(f"Unexpected content type: {type(text_content)}")
        
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Sometimes Claude returns JSON wrapped in markdown code blocks
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
            
    except ValueError as ve:
        # Re-raise ValueError (content filter blocks) as-is so caller can handle
        raise ve
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response: {str(e)}")
    except Exception as error:
        raise Exception(f"Failed to generate JSON: {str(error)}")
