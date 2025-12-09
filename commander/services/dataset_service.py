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
        if "conversation" in example:
            conv = example["conversation"]
            if isinstance(conv, list) and len(conv) >= 2:
                user_msg = None
                assistant_msg = None
                
                for msg in conv:
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
        
        # Try messages format
        if "messages" in example:
            messages = example["messages"]
            if isinstance(messages, list) and len(messages) >= 2:
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


def _score_example_relevance(example: Dict[str, str], issue_description: str, issue_hash: str = None) -> float:
    """
    Use LLM to score how relevant an example is to the issue.
    Returns a relevance score from 0-100.
    """
    user_msg = example.get("user", "")[:500]  # Truncate to avoid token limits
    assistant_msg = example.get("assistant", "")[:500]
    
    prompt = f"""Score how relevant this user-assistant interaction is to the following issue.

ISSUE: "{issue_description}"

INTERACTION:
User: {user_msg}
Assistant: {assistant_msg}

SCORING CRITERIA:
- 90-100: This interaction CLEARLY demonstrates the issue
- 70-89: This interaction is RELATED to the issue (similar context, partial match)
- 40-69: This interaction is SOMEWHAT related (shares some keywords/concepts)
- 0-39: This interaction is NOT related to the issue

Consider:
- Does the assistant's response show the problem described in the issue?
- Is the topic/domain similar to what the issue describes?
- Could this example be useful for training a classifier to detect this issue?

OUTPUT FORMAT (JSON):
{{
    "relevance_score": <0-100>,
    "reasoning": "Brief explanation (max 50 words)"
}}

Return only valid JSON, no other text."""

    try:
        result = generate_json(prompt, temperature=0.2, task_type="classification", issue_hash=issue_hash)
        
        if isinstance(result, dict):
            score = result.get("relevance_score", 0)
            if isinstance(score, (int, float)):
                return float(score)
        return 0.0
    except Exception as e:
        print(f"WARNING: Failed to score example relevance: {e}")
        return 0.0


def sample_relevant_examples_from_wildchat(
    issue_description: str,
    num_examples: int = 12,
    issue_hash: str = None
) -> List[Dict[str, str]]:
    """
    Sample the most relevant examples from WildChat dataset for the given issue.
    
    Args:
        issue_description: The issue description to find examples for
        num_examples: Number of examples to return
        issue_hash: Optional hash for cache isolation
        
    Returns:
        List of examples in format: [{"user": "...", "assistant": "...", "relevance_score": ...}]
    """
    print(f"DEBUG: Sampling {num_examples} relevant examples from WildChat for issue: '{issue_description[:50]}...'")
    
    # Load dataset
    try:
        dataset, dataset_size = _load_wildchat_dataset()
    except Exception as e:
        print(f"ERROR: Failed to load WildChat dataset: {e}")
        raise
    
    # Use issue hash to seed random sampling (for reproducibility)
    if issue_hash:
        random.seed(int(issue_hash[:8], 16))
    
    # Sample a larger pool to find relevant examples (5x target)
    sample_pool_size = min(num_examples * 5, dataset_size, 100)  # Cap at 100 to limit LLM calls
    print(f"DEBUG: Sampling {sample_pool_size} candidates from dataset of size {dataset_size:,}")
    
    # Randomly sample indices
    sampled_indices = random.sample(range(dataset_size), sample_pool_size)
    
    # Extract conversations and score relevance
    scored_examples = []
    
    for idx in sampled_indices:
        try:
            example = dataset[idx]
            conversation = _extract_conversation_from_wildchat(example)
            
            if not conversation:
                continue
            
            # Skip very short conversations
            if len(conversation.get("user", "")) < 20 or len(conversation.get("assistant", "")) < 20:
                continue
            
            # Score relevance to the issue
            relevance_score = _score_example_relevance(conversation, issue_description, issue_hash)
            
            if relevance_score > 30:  # Only keep somewhat relevant examples
                scored_examples.append({
                    "user": conversation["user"],
                    "assistant": conversation["assistant"],
                    "relevance_score": relevance_score
                })
                print(f"DEBUG: Found example with relevance score {relevance_score}")
                
                # Stop once we have enough high-quality examples
                if len(scored_examples) >= num_examples * 2:
                    break
            
        except Exception as e:
            print(f"WARNING: Failed to process example at index {idx}: {e}")
            continue
    
    # Sort by relevance and take top examples
    scored_examples.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    top_examples = scored_examples[:num_examples]
    
    print(f"DEBUG: Returning {len(top_examples)} most relevant examples from WildChat")
    
    if top_examples:
        avg_score = sum(e.get("relevance_score", 0) for e in top_examples) / len(top_examples)
        print(f"DEBUG: Average relevance score: {avg_score:.1f}")
    
    return top_examples
