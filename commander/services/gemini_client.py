import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from typing import Optional
from commander.services.cache_service import (
    get_cached_result,
    set_cached_result
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
    timeout=60.0,
    max_retries=2
)


def generate_text(
    prompt: str, 
    temperature: float = 0.7, 
    max_tokens: int = 2048,
    task_type: str = "reasoning",
    issue_hash: str = None
) -> str:
    """
    Generate text using Anthropic Claude API with caching.
    
    Args:
        prompt: The prompt to send to Claude
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        task_type: Type of task for caching purposes
        issue_hash: Optional hash of the issue description for cache isolation
    
    Returns:
        Generated text string
    """
    try:
        # Check cache first
        cached_result = get_cached_result(prompt, task_type, temperature, issue_hash)
        if cached_result is not None:
            if isinstance(cached_result, str):
                return cached_result
            elif isinstance(cached_result, dict) and "text" in cached_result:
                return cached_result["text"]
        
        # Make API call
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=60.0,
        )
        
        if not response.content or len(response.content) == 0:
            raise Exception("Response blocked: No content returned.")
        
        # Claude returns content as a list of text blocks
        text_content = response.content[0]
        if hasattr(text_content, 'text'):
            result_text = text_content.text
        elif isinstance(text_content, str):
            result_text = text_content
        else:
            raise Exception(f"Unexpected content type: {type(text_content)}")
        
        # Cache the result
        set_cached_result(prompt, result_text, task_type, temperature, issue_hash)
        
        return result_text
            
    except Exception as error:
        raise Exception(f"Failed to generate text: {str(error)}")


def generate_json(
    prompt: str, 
    temperature: float = 0.3,
    task_type: str = "analysis",
    issue_hash: str = None
) -> dict:
    """
    Generate JSON response using Anthropic Claude API with caching.
    
    Args:
        prompt: The prompt to send to Claude
        temperature: Sampling temperature (0.0-1.0)
        task_type: Type of task for caching purposes
        issue_hash: Optional hash of the issue description for cache isolation
    
    Returns:
        Parsed JSON dictionary
    """
    try:
        # Check cache first
        cached_result = get_cached_result(prompt, task_type, temperature, issue_hash)
        if cached_result is not None:
            if isinstance(cached_result, dict):
                if len(cached_result) > 0:
                    return cached_result
            elif isinstance(cached_result, str):
                try:
                    parsed = json.loads(cached_result)
                    if isinstance(parsed, dict) and len(parsed) > 0:
                        return parsed
                except json.JSONDecodeError:
                    pass
        
        # Add instruction to return JSON
        json_prompt = prompt + "\n\nReturn only valid JSON, no other text."
        
        # Make API call
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {"role": "user", "content": json_prompt}
            ],
            timeout=60.0,
        )
        
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
            parsed_json = json.loads(text)
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
            try:
                parsed_json = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse JSON response: {e}")
                print(f"DEBUG: Response text (first 500 chars): {text[:500]}")
                raise Exception(f"Failed to parse JSON response: {str(e)}")
        
        # Validate parsed JSON before caching
        if not parsed_json or (isinstance(parsed_json, dict) and len(parsed_json) == 0):
            raise Exception("LLM returned empty JSON response")
        
        # Cache the result
        set_cached_result(prompt, parsed_json, task_type, temperature, issue_hash)
        
        return parsed_json
            
    except ValueError as ve:
        raise ve
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response: {str(e)}")
    except Exception as error:
        raise Exception(f"Failed to generate JSON: {str(error)}")
