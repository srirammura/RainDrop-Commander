"""Agent to evaluate if an example can form a solid generalized rule."""
from typing import Dict, Any
from commander.services.gemini_client import generate_json


def evaluate_rule_potential(example: Dict[str, str], issue_description: str, issue_hash: str = None) -> Dict[str, Any]:
    """
    Evaluate if an example has high potential for forming a solid generalized rule.
    
    Args:
        example: Dict with "user" and "assistant" keys
        issue_description: The original issue description
        
    Returns:
        Dict with "score" (0-100) and "reasoning" keys
    """
    user_msg = example.get("user", "")
    assistant_msg = example.get("assistant", "")
    
    prompt = f"""Evaluate if this example has high potential for forming a solid, generalized classification rule.

ISSUE DESCRIPTION: "{issue_description}"

EXAMPLE:
User: {user_msg}
Assistant: {assistant_msg}

EVALUATION CRITERIA:
1. Clarity: Does the example clearly demonstrate the issue?
2. Generalizability: Can this example be used to create a rule that applies to similar cases?
3. Specificity: Does it have distinguishing features that can be captured in a rule?
4. Coverage: Would a rule based on this example catch similar issues?

Score from 0-100 where:
- 90-100: Excellent - can form a strong, generalizable rule
- 70-89: Good - can form a decent rule with some limitations
- 50-69: Moderate - rule would be narrow or have gaps
- 0-49: Poor - example is too specific or unclear for rule formation

OUTPUT FORMAT (JSON):
{{
    "score": 85,
    "reasoning": "Brief explanation of why this score was assigned"
}}

Return only valid JSON, no other text."""

    try:
        result = generate_json(prompt, temperature=0.3, task_type="validation")
        
        if isinstance(result, dict) and "score" in result:
            score = int(result.get("score", 50))
            # Clamp score to 0-100
            score = max(0, min(100, score))
            return {
                "score": score,
                "reasoning": result.get("reasoning", "No reasoning provided")
            }
        else:
            # Default score if parsing fails
            return {
                "score": 50,
                "reasoning": "Evaluation failed, using default score"
            }
            
    except Exception as e:
        print(f"WARNING: Rule potential evaluation failed for example: {e}")
        # Return default score on error
        return {
            "score": 50,
            "reasoning": f"Evaluation error: {str(e)}"
        }

