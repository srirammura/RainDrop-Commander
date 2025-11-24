import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"  # Using GPT-4o-mini for cost efficiency

if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=API_KEY)


def generate_text(prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """Generate text using OpenAI API."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        if not response.choices or len(response.choices) == 0:
            raise Exception("Response blocked: No choices returned.")
        
        choice = response.choices[0]
        
        # Check if content was filtered
        if choice.finish_reason == "content_filter":
            raise Exception("Response blocked by content filter. The content may violate safety guidelines.")
        
        if not choice.message or not choice.message.content:
            raise Exception(f"Response blocked: No content returned (finish_reason: {choice.finish_reason}).")
        
        return choice.message.content
    except Exception as error:
        raise Exception(f"Failed to generate text: {str(error)}")


def generate_json(prompt: str, temperature: float = 0.3) -> dict:
    """Generate JSON response using OpenAI API."""
    try:
        # Add instruction to return JSON
        json_prompt = prompt + "\n\nReturn only valid JSON, no other text."
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                {"role": "user", "content": json_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"},  # Force JSON mode
        )
        
        if not response.choices or len(response.choices) == 0:
            raise Exception("Response blocked: No choices returned.")
        
        choice = response.choices[0]
        
        # Check if content was filtered
        if choice.finish_reason == "content_filter":
            raise ValueError("Response blocked by content filter. The content may violate safety guidelines.")
        
        if not choice.message or not choice.message.content:
            raise ValueError(f"Response blocked: No content returned (finish_reason: {choice.finish_reason}).")
        
        text = choice.message.content
        
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Sometimes OpenAI returns JSON wrapped in markdown code blocks
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
