"""Agent to identify genres/categories of an issue and generate focused prompts for each genre."""
from typing import List, Dict, Any
from commander.services.gemini_client import generate_json


def identify_genres(issue_description: str) -> List[Dict[str, str]]:
    """
    Analyze issue description to identify distinct genres/categories.
    Returns a list of genre prompts, each optimized to generate 1-2 examples.
    
    Args:
        issue_description: The user's issue description
        
    Returns:
        List of dicts with "name" and "prompt" keys for each genre
    """
    prompt = f"""Analyze the following issue description and identify 3-6 distinct genres/categories that represent different ways this issue can manifest.

ISSUE DESCRIPTION: "{issue_description}"

Your task:
1. Identify 3-6 distinct genres/categories of this issue
2. Each genre should represent a different manifestation or context where this issue occurs
3. For each genre, create a focused prompt that will generate 1-2 realistic production examples

GENRE CRITERIA:
- Each genre should be distinct (different contexts, technologies, or scenarios)
- Genres should cover diverse manifestations of the issue
- Each genre prompt should be specific enough to generate focused examples
- Total examples across all genres should be 10-12

OUTPUT FORMAT (JSON):
{{
    "genres": [
        {{
            "name": "Genre name (e.g., 'API Documentation Access Failure')",
            "description": "Brief description of this genre",
            "prompt": "Focused prompt to generate 1-2 examples for this genre. The prompt should be self-contained and include the issue description."
        }},
        ...
    ]
}}

Return only valid JSON, no other text."""

    try:
        result = generate_json(prompt, temperature=0.5, task_type="analysis")
        
        if isinstance(result, dict) and "genres" in result:
            genres = result["genres"]
            # Validate and ensure we have 3-6 genres
            if len(genres) < 3:
                print(f"WARNING: Only {len(genres)} genres identified, expected 3-6")
            elif len(genres) > 6:
                genres = genres[:6]
                print(f"WARNING: {len(genres)} genres identified, limiting to 6")
            
            # Ensure each genre has required fields
            validated_genres = []
            for genre in genres:
                if "name" in genre and "prompt" in genre:
                    validated_genres.append({
                        "name": genre["name"],
                        "description": genre.get("description", ""),
                        "prompt": genre["prompt"]
                    })
            
            if len(validated_genres) >= 3:
                return validated_genres
            else:
                # Fallback: create default genres if validation fails
                print("WARNING: Genre validation failed, using fallback genres")
                return _create_fallback_genres(issue_description)
        else:
            print("WARNING: Invalid genre identification result, using fallback")
            return _create_fallback_genres(issue_description)
            
    except Exception as e:
        print(f"ERROR: Genre identification failed: {e}")
        return _create_fallback_genres(issue_description)


def _create_fallback_genres(issue_description: str) -> List[Dict[str, str]]:
    """Create fallback genres if LLM call fails."""
    return [
        {
            "name": "Primary Manifestation",
            "description": "Main way the issue occurs",
            "prompt": f"""Generate 2-3 realistic production examples of the following issue:

ISSUE: "{issue_description}"

Create user-assistant interactions that clearly demonstrate this issue. Examples should be specific, use real technology names, and show realistic production scenarios."""
        },
        {
            "name": "Edge Case Manifestation",
            "description": "Edge cases or boundary scenarios",
            "prompt": f"""Generate 2-3 realistic production examples of edge cases or boundary scenarios for this issue:

ISSUE: "{issue_description}"

Create user-assistant interactions that show subtle or edge-case manifestations of this issue."""
        },
        {
            "name": "Different Context Manifestation",
            "description": "Issue occurring in different contexts",
            "prompt": f"""Generate 2-3 realistic production examples of this issue occurring in different contexts or with different technologies:

ISSUE: "{issue_description}"

Create diverse examples showing the issue in various contexts."""
        }
    ]

