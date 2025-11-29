import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-3-5-sonnet-20241022"  # Using Claude 3.5 Sonnet for best performance

if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Create client with timeout settings
client = Anthropic(
    api_key=API_KEY,
    timeout=60.0,  # 60 second timeout for individual API calls
    max_retries=2  # Retry up to 2 times on failure
)


def generate_text(prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """Generate text using Anthropic Claude API."""
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=60.0,  # 60 second timeout for this specific call
        )
        
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


def generate_json(prompt: str, temperature: float = 0.3) -> dict:
    """Generate JSON response using Anthropic Claude API."""
    try:
        # Add instruction to return JSON
        json_prompt = prompt + "\n\nReturn only valid JSON, no other text."
        
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {"role": "user", "content": json_prompt}
            ],
            timeout=60.0,  # 60 second timeout for this specific call
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
