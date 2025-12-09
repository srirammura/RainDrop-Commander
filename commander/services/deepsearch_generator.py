"""Service to generate DeepSearch examples and rules from issue descriptions."""
from typing import List, Dict, Any
from commander.services.gemini_client import generate_json
from commander.services.dataset_service import sample_relevant_examples_from_wildchat
import json
import re
import hashlib


def generate_examples_from_issue(issue_description: str) -> List[Dict[str, str]]:
    """
    Sample relevant interaction examples from WildChat dataset for the issue.
    
    Returns a list of examples that are most relevant to the issue description.
    These examples represent real production data.
    """
    print(f"DEBUG: ===== generate_examples_from_issue() CALLED =====")
    print(f"DEBUG: Issue description: '{issue_description}'")
    print(f"DEBUG: Sampling from WildChat dataset")
    
    # Compute issue hash for cache isolation
    issue_hash = hashlib.md5(issue_description.encode('utf-8')).hexdigest()
    print(f"DEBUG: Issue hash: {issue_hash}")
    
    # Sample relevant examples from WildChat dataset
    try:
        examples = sample_relevant_examples_from_wildchat(
            issue_description, 
            num_examples=12, 
            issue_hash=issue_hash
        )
        print(f"DEBUG: Sampled {len(examples)} examples from WildChat")
    except Exception as e:
        print(f"ERROR: Failed to sample examples from WildChat: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Validate we have enough examples
    if len(examples) >= 4:
        print(f"DEBUG: Returning {len(examples)} relevant examples")
        
        # Log first example
        if examples:
            first_example = examples[0]
            print(f"DEBUG: Top example - User: '{first_example.get('user', '')[:100]}...'")
            print(f"DEBUG: Top example - Assistant: '{first_example.get('assistant', '')[:100]}...'")
            print(f"DEBUG: Top example - Relevance: {first_example.get('relevance_score', 'N/A')}")
        
        return examples
    elif len(examples) > 0:
        print(f"WARNING: Only found {len(examples)} examples (minimum 4 required), continuing with partial results")
        return examples
    else:
        print(f"ERROR: No relevant examples found for issue: '{issue_description}'")
        raise Exception(f"Failed to find relevant examples from WildChat dataset.")


def construct_rules_prompt(user_description: str, examples: List[Dict[str, str]]) -> str:
    """
    Construct the rules generation prompt based on relevant examples.
    
    The rules generated will be used to:
    1. Generate thousands of training examples via LLM
    2. Train classifier models to detect this specific issue
    3. Scan production data to find all occurrences of the issue
    """
    # Format examples for the prompt
    examples_text = ""
    for i, ex in enumerate(examples, 1):
        user = ex.get("user", "")[:500]
        assistant = ex.get("assistant", "")[:500]
        relevance = ex.get("relevance_score", "N/A")
        examples_text += f"""
Example {i} (Relevance: {relevance}):
User: {user}
Assistant: {assistant}
---
"""
    
    prompt = f"""You are a Senior Classification Engineer creating rules for an AI issue detection system.

CONTEXT:
- These rules will be used to generate THOUSANDS of training examples via LLM
- Those examples will train a classifier model specific to this issue
- The classifier will scan millions of production conversations to find this issue
- Rules must be PRECISE enough to generate diverse, high-quality training data
- Rules must be GENERAL enough to catch variations of the issue

USER'S ISSUE DESCRIPTION:
"{user_description}"

RELEVANT PRODUCTION EXAMPLES:
{examples_text}

YOUR TASK:
Generate 4 actionable classification rules that:
1. Capture the CORE pattern of the issue
2. Are specific enough to avoid false positives
3. Are general enough to catch variations
4. Can be used to generate diverse training examples

RULE FORMAT REQUIREMENTS:
Each rule must be in this format:
- "The [output|input] must [express|contain|indicate] [specific condition]"
- "The [output|input] must not [contain|be] [exclusion condition]"

EXAMPLES OF GOOD RULES:
- "The output must express the assistant failing to access documentation"
- "The input must not be the user having trouble searching docs"
- "The assistant response must indicate inability to retrieve external resources"

OUTPUT FORMAT (JSON):
{{
    "rules": [
        {{
            "rule_id": 1,
            "rule": "The output must express [specific pattern]",
            "description": "What this rule detects",
            "example": "Example text from the production data that matches this rule",
            "keywords": ["keyword1", "keyword2"],
            "training_guidance": "How to use this rule to generate training examples"
        }},
        // ... 3 more rules
    ],
    "coverage_notes": "How these 4 rules together cover the issue comprehensively"
}}

CRITICAL INSTRUCTIONS:
1. Rules must be ACTIONABLE - they will be used to generate training data
2. Each rule should capture a DIFFERENT aspect or manifestation of the issue
3. Include specific keywords/phrases that appear in the examples
4. Think about edge cases and variations the classifier should catch
5. Rules should work together to provide comprehensive coverage

Return only valid JSON, no other text."""

    return prompt


def generate_rules_from_examples(
    issue_description: str, 
    examples: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Generate classification rules from relevant production examples.
    
    These rules will be used to generate training data for classifier models.
    """
    print(f"DEBUG: ===== generate_rules_from_examples() CALLED =====")
    print(f"DEBUG: Issue description: '{issue_description}'")
    print(f"DEBUG: Number of examples: {len(examples)}")
    
    # Compute issue hash for cache isolation
    issue_hash = hashlib.md5(issue_description.encode('utf-8')).hexdigest()
    
    # Build the prompt
    prompt = construct_rules_prompt(issue_description, examples)
    
    try:
        result = generate_json(prompt, temperature=0.5, task_type="rule_generation", issue_hash=issue_hash)
        
        if isinstance(result, dict) and "rules" in result:
            rules = result["rules"]
            print(f"DEBUG: Generated {len(rules)} rules")
            
            # Format rules for display
            formatted_rules = []
            for rule in rules:
                formatted_rule = {
                    "title": rule.get("rule", "Untitled Rule"),
                    "description": rule.get("description", ""),
                    "example": rule.get("example", ""),
                    "keywords": rule.get("keywords", []),
                    "training_guidance": rule.get("training_guidance", "")
                }
                formatted_rules.append(formatted_rule)
            
            return formatted_rules
        else:
            print(f"WARNING: Unexpected response format: {type(result)}")
            return []
            
    except Exception as e:
        print(f"ERROR: Failed to generate rules: {e}")
        import traceback
        traceback.print_exc()
        raise


# Keep old function name for backwards compatibility
def generate_suggested_rules_from_examples(
    issue_description: str, 
    examples: List[Dict[str, str]],
    rule_potential_scores: Dict[int, Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """
    Backwards compatible wrapper for generate_rules_from_examples.
    The rule_potential_scores parameter is ignored in the new implementation.
    """
    return generate_rules_from_examples(issue_description, examples)
