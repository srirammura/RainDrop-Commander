"""Service to load and sample from WildChat dataset for production examples."""
from typing import List, Dict, Any, Optional
from datasets import load_dataset
from commander.services.gemini_client import generate_json
import random
import hashlib


# Cache the loaded dataset
_wildchat_dataset = None
_wildchat_dataset_size = None


def _load_wildchat_dataset():
    """Load WildChat dataset (cached after first load)."""
    global _wildchat_dataset, _wildchat_dataset_size
    
    if _wildchat_dataset is None:
        print("DEBUG: Loading WildChat dataset...")
        try:
            # Load the dataset
            ds = load_dataset("allenai/WildChat", split="train")
            _wildchat_dataset = ds
            _wildchat_dataset_size = len(ds)
            print(f"DEBUG: WildChat dataset loaded. Size: {_wildchat_dataset_size:,} examples")
        except Exception as e:
            print(f"ERROR: Failed to load WildChat dataset: {e}")
            raise
    
    return _wildchat_dataset, _wildchat_dataset_size


def _extract_conversation_from_wildchat(example: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract user and assistant messages from WildChat example.
    WildChat format may vary, so we handle multiple possible structures.
    """
    try:
        # Try different possible field names
        if "messages" in example:
            messages = example["messages"]
            if isinstance(messages, list) and len(messages) >= 2:
                # Find user and assistant messages
                user_msg = None
                assistant_msg = None
                
                for msg in messages:
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "")
                    
                    if role == "user" and not user_msg:
                        user_msg = content
                    elif role in ["assistant", "model"] and not assistant_msg:
                        assistant_msg = content
                
                if user_msg and assistant_msg:
                    return {
                        "user": user_msg,
                        "assistant": assistant_msg
                    }
        
        # Try alternative format
        if "conversation" in example:
            conv = example["conversation"]
            if isinstance(conv, list) and len(conv) >= 2:
                user_msg = conv[0].get("content", "") if conv[0].get("role", "").lower() == "user" else None
                assistant_msg = conv[1].get("content", "") if conv[1].get("role", "").lower() in ["assistant", "model"] else None
                
                if user_msg and assistant_msg:
                    return {
                        "user": user_msg,
                        "assistant": assistant_msg
                    }
        
        # Try direct fields
        if "user" in example and "assistant" in example:
            return {
                "user": str(example["user"]),
                "assistant": str(example["assistant"])
            }
        
        # Try prompt/response format
        if "prompt" in example and "response" in example:
            return {
                "user": str(example["prompt"]),
                "assistant": str(example["response"])
            }
        
        return None
        
    except Exception as e:
        print(f"WARNING: Failed to extract conversation from WildChat example: {e}")
        return None


def _classify_example_relevance(example: Dict[str, str], issue_description: str, issue_hash: str = None) -> Dict[str, Any]:
    """
    Use LLM to classify if an example is relevant to the issue (MATCH) or not (NO_MATCH).
    Returns classification with category and reasoning.
    """
    user_msg = example.get("user", "")
    assistant_msg = example.get("assistant", "")
    
    prompt = f"""Classify whether this user-assistant interaction demonstrates the following issue:

ISSUE: "{issue_description}"

INTERACTION:
User: {user_msg}
Assistant: {assistant_msg}

CLASSIFICATION TASK:
1. Does this interaction clearly demonstrate the issue? (MATCH - SIMPLE_POSITIVE)
2. Does this interaction clearly NOT demonstrate the issue? (NO_MATCH - SIMPLE_NEGATIVE)
3. Does this interaction demonstrate the issue but in a subtle/indirect way? (MATCH - BOUNDARY_POSITIVE)
4. Does this interaction share keywords with the issue but does NOT actually demonstrate it? (NO_MATCH - BOUNDARY_NEGATIVE)

OUTPUT FORMAT (JSON):
{{
    "user_label": "MATCH" or "NO_MATCH",
    "category": "SIMPLE_POSITIVE" or "SIMPLE_NEGATIVE" or "BOUNDARY_POSITIVE" or "BOUNDARY_NEGATIVE",
    "reasoning": "Brief explanation of why this classification was chosen",
    "relevance_score": 0-100 (how relevant is this example to the issue)
}}

Return only valid JSON, no other text."""

    try:
        result = generate_json(prompt, temperature=0.3, task_type="classification", issue_hash=issue_hash)
        
        if isinstance(result, dict):
            user_label = result.get("user_label", "NO_MATCH")
            category = result.get("category", "SIMPLE_NEGATIVE")
            reasoning = result.get("reasoning", "")
            relevance_score = result.get("relevance_score", 50)
            
            return {
                "user_label": user_label,
                "category": category,
                "reasoning": reasoning,
                "relevance_score": relevance_score
            }
        else:
            # Default classification
            return {
                "user_label": "NO_MATCH",
                "category": "SIMPLE_NEGATIVE",
                "reasoning": "Classification failed, defaulting to NO_MATCH",
                "relevance_score": 0
            }
    except Exception as e:
        print(f"WARNING: Failed to classify example relevance: {e}")
        return {
            "user_label": "NO_MATCH",
            "category": "SIMPLE_NEGATIVE",
            "reasoning": f"Classification error: {str(e)}",
            "relevance_score": 0
        }


def sample_examples_from_wildchat(
    issue_description: str,
    num_examples: int = 12,
    issue_hash: str = None
) -> List[Dict[str, str]]:
    """
    Sample examples from WildChat dataset that are relevant to the issue.
    
    Args:
        issue_description: The issue description to match against
        num_examples: Number of examples to sample (target)
        issue_hash: Optional hash for cache isolation
        
    Returns:
        List of examples in format: [{"user": "...", "assistant": "...", "user_label": "MATCH/NO_MATCH", "category": "...", "topic": "..."}]
    """
    print(f"DEBUG: Sampling {num_examples} examples from WildChat dataset for issue: '{issue_description[:50]}...'")
    
    # Load dataset
    try:
        dataset, dataset_size = _load_wildchat_dataset()
    except Exception as e:
        print(f"ERROR: Failed to load WildChat dataset: {e}")
        raise
    
    # Use issue hash to seed random sampling (for reproducibility)
    if issue_hash:
        random.seed(int(issue_hash[:8], 16))  # Use first 8 hex chars as seed
    
    # Sample a larger pool first (3x target) to account for filtering
    sample_pool_size = min(num_examples * 3, dataset_size)
    print(f"DEBUG: Sampling {sample_pool_size} candidates from dataset of size {dataset_size:,}")
    
    # Randomly sample indices
    sampled_indices = random.sample(range(dataset_size), sample_pool_size)
    
    # Extract conversations and classify them
    classified_examples = []
    match_count = 0
    no_match_count = 0
    
    target_matches = int(num_examples * 0.6)  # 60% MATCH
    target_no_matches = num_examples - target_matches  # 40% NO_MATCH
    
    print(f"DEBUG: Target distribution: {target_matches} MATCH, {target_no_matches} NO_MATCH")
    
    for idx in sampled_indices:
        if len(classified_examples) >= num_examples:
            break
        
        try:
            example = dataset[idx]
            conversation = _extract_conversation_from_wildchat(example)
            
            if not conversation:
                continue
            
            # Classify relevance
            classification = _classify_example_relevance(conversation, issue_description, issue_hash)
            
            user_label = classification["user_label"]
            category = classification["category"]
            
            # Check if we need more of this type
            if user_label == "MATCH":
                if match_count < target_matches:
                    classified_examples.append({
                        "user": conversation["user"],
                        "assistant": conversation["assistant"],
                        "user_label": user_label,
                        "category": category,
                        "topic": classification.get("reasoning", "")[:100],  # Use reasoning as topic
                        "relevance_score": classification.get("relevance_score", 50)
                    })
                    match_count += 1
                    print(f"DEBUG: Added MATCH example ({match_count}/{target_matches})")
            else:  # NO_MATCH
                if no_match_count < target_no_matches:
                    classified_examples.append({
                        "user": conversation["user"],
                        "assistant": conversation["assistant"],
                        "user_label": user_label,
                        "category": category,
                        "topic": classification.get("reasoning", "")[:100],
                        "relevance_score": classification.get("relevance_score", 0)
                    })
                    no_match_count += 1
                    print(f"DEBUG: Added NO_MATCH example ({no_match_count}/{target_no_matches})")
            
        except Exception as e:
            print(f"WARNING: Failed to process example at index {idx}: {e}")
            continue
    
    print(f"DEBUG: Sampled {len(classified_examples)} examples from WildChat ({match_count} MATCH, {no_match_count} NO_MATCH)")
    
    # If we don't have enough examples, try to fill with what we have
    if len(classified_examples) < num_examples:
        print(f"WARNING: Only found {len(classified_examples)} examples, target was {num_examples}")
    
    return classified_examples

