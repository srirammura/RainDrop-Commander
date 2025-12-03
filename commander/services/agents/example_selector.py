"""Agent to select top 4 examples that have highest potential for forming strong generalized rules."""
from typing import List, Dict, Any
from commander.services.gemini_client import generate_json


def select_top_examples(
    labeled_examples: List[Dict[str, Any]], 
    issue_description: str,
    rule_potential_scores: Dict[int, Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Select top 4 examples (can be 2 examples repeated twice) that have highest potential
    for forming strong generalized rules.
    
    Args:
        labeled_examples: List of examples with "user", "assistant", "user_label" keys
        issue_description: The original issue description
        rule_potential_scores: Optional dict mapping example index to rule potential scores
        
    Returns:
        List of 4 selected examples (can include duplicates)
    """
    if not labeled_examples:
        return []
    
    # Filter to MATCH examples only (we generate rules from positive examples)
    match_examples = [
        (i, ex) for i, ex in enumerate(labeled_examples) 
        if ex.get("user_label") == "MATCH"
    ]
    
    if len(match_examples) == 0:
        print("WARNING: No MATCH examples found for rule generation")
        return []
    
    # If we have rule potential scores, include them in the prompt
    scores_text = ""
    if rule_potential_scores:
        scores_text = "\n\nRULE POTENTIAL SCORES:\n"
        for idx, score_data in rule_potential_scores.items():
            if idx < len(labeled_examples):
                ex = labeled_examples[idx]
                scores_text += f"Example {idx}: Score {score_data.get('score', 50)} - {score_data.get('reasoning', '')}\n"
    
    # Format examples for prompt
    examples_text = ""
    for i, (orig_idx, ex) in enumerate(match_examples):
        examples_text += f"\nExample {i} (Original Index {orig_idx}):\n"
        examples_text += f"User: {ex.get('user', '')}\n"
        examples_text += f"Assistant: {ex.get('assistant', '')}\n"
    
    prompt = f"""Select the top 4 examples that have the highest potential for forming strong, generalized classification rules.

ISSUE DESCRIPTION: "{issue_description}"

AVAILABLE EXAMPLES:{examples_text}{scores_text}

SELECTION CRITERIA:
1. Choose examples that can form rules with high precision and recall
2. Prefer diverse examples that cover different aspects of the issue
3. If needed, you can select the same example twice (if it's exceptionally good)
4. Prioritize examples with clear, distinguishable features
5. Consider rule potential scores if provided

OUTPUT FORMAT (JSON):
{{
    "selected_examples": [
        {{
            "example_index": 0,
            "reason": "Why this example was selected"
        }},
        ...
    ]
}}

IMPORTANT: Return exactly 4 examples. You can repeat an example index if needed.

Return only valid JSON, no other text."""

    try:
        result = generate_json(prompt, temperature=0.4, task_type="analysis")
        
        if isinstance(result, dict) and "selected_examples" in result:
            selected = result["selected_examples"]
            
            # Validate and ensure we have 4 selections
            if len(selected) < 4:
                print(f"WARNING: Only {len(selected)} examples selected, expected 4")
                # Pad with last example if needed
                while len(selected) < 4 and len(selected) > 0:
                    selected.append(selected[-1])
            elif len(selected) > 4:
                selected = selected[:4]
            
            # Map back to actual examples
            selected_examples = []
            for sel in selected:
                example_idx = sel.get("example_index", 0)
                # Find the original example
                if 0 <= example_idx < len(match_examples):
                    orig_idx, ex = match_examples[example_idx]
                    selected_examples.append({
                        **ex,
                        "selection_reason": sel.get("reason", ""),
                        "original_index": orig_idx
                    })
                else:
                    # Invalid index, use first example
                    if match_examples:
                        orig_idx, ex = match_examples[0]
                        selected_examples.append({
                            **ex,
                            "selection_reason": "Invalid index, using first example",
                            "original_index": orig_idx
                        })
            
            # Ensure we have exactly 4
            while len(selected_examples) < 4 and len(match_examples) > 0:
                # Repeat last example or first if needed
                if selected_examples:
                    selected_examples.append(selected_examples[-1])
                else:
                    orig_idx, ex = match_examples[0]
                    selected_examples.append({
                        **ex,
                        "selection_reason": "Padding to reach 4 examples",
                        "original_index": orig_idx
                    })
            
            return selected_examples[:4]
            
        else:
            # Fallback: select first 4 MATCH examples
            print("WARNING: Invalid selection result, using first 4 MATCH examples")
            return [ex for _, ex in match_examples[:4]]
            
    except Exception as e:
        print(f"ERROR: Example selection failed: {e}")
        # Fallback: return first 4 MATCH examples
        return [ex for _, ex in match_examples[:4]]

