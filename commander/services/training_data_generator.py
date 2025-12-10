"""Service to generate training data from accepted rules using LLM."""
from typing import List, Dict, Any
from commander.services.gemini_client import generate_json
import hashlib
import json
import os


def generate_training_examples_from_rule(
    rule: Dict[str, Any],
    issue_description: str,
    num_positive: int = 100,
    num_negative: int = 100,
    issue_hash: str = None
) -> Dict[str, List[Dict[str, str]]]:
    """
    Generate training examples from a single rule.
    
    Args:
        rule: The rule to generate examples from
        issue_description: The original issue description
        num_positive: Number of positive (MATCH) examples to generate
        num_negative: Number of negative (NO_MATCH) examples to generate
        issue_hash: Optional hash for cache isolation
        
    Returns:
        Dict with 'positive' and 'negative' lists of examples
    """
    print(f"DEBUG: Generating training examples from rule: {rule.get('title', 'Unknown')}")
    
    rule_title = rule.get('title', '')
    rule_description = rule.get('description', '')
    rule_example = rule.get('example', '')
    keywords = rule.get('keywords', [])
    training_guidance = rule.get('training_guidance', '')
    
    # Generate positive examples
    positive_prompt = f"""Generate {num_positive} diverse training examples that MATCH the following rule.

ISSUE: "{issue_description}"

RULE: {rule_title}
DESCRIPTION: {rule_description}
EXAMPLE: {rule_example}
KEYWORDS: {', '.join(keywords) if keywords else 'N/A'}
TRAINING GUIDANCE: {training_guidance}

REQUIREMENTS:
1. Each example must clearly demonstrate the issue described in the rule
2. Vary the technical context (different technologies, frameworks, tools)
3. Vary the user personas (beginners, experts, different industries)
4. Vary the phrasing and communication style
5. Include realistic technical details
6. Some examples should be subtle, others obvious
7. Each example should be a user-assistant conversation

OUTPUT FORMAT (JSON):
{{
    "examples": [
        {{
            "user": "User's message",
            "assistant": "Assistant's response that demonstrates the issue",
            "label": "MATCH"
        }},
        ...
    ]
}}

Generate exactly {num_positive} diverse examples. Return only valid JSON."""

    negative_prompt = f"""Generate {num_negative} diverse training examples that do NOT match the following rule (negative examples).

ISSUE TO AVOID: "{issue_description}"

RULE: {rule_title}
DESCRIPTION: {rule_description}
KEYWORDS TO INCLUDE (but not as the issue): {', '.join(keywords) if keywords else 'N/A'}

REQUIREMENTS:
1. Examples should NOT demonstrate the issue - they are successful interactions
2. Some should contain similar keywords but NOT be the actual issue (hard negatives)
3. Vary the technical context (different technologies, frameworks, tools)
4. Include examples where:
   - User mentions the topic but assistant successfully helps
   - Similar keywords appear but in different context
   - User has trouble but assistant resolves it
   - Successful documentation retrieval
   - Normal helpful interactions
5. Each example should be a user-assistant conversation

OUTPUT FORMAT (JSON):
{{
    "examples": [
        {{
            "user": "User's message",
            "assistant": "Assistant's helpful response (no issue)",
            "label": "NO_MATCH"
        }},
        ...
    ]
}}

Generate exactly {num_negative} diverse negative examples. Return only valid JSON."""

    positive_examples = []
    negative_examples = []
    
    try:
        # Generate positive examples
        print(f"DEBUG: Generating {num_positive} positive examples...")
        result = generate_json(positive_prompt, temperature=0.8, task_type="generation", issue_hash=issue_hash)
        if isinstance(result, dict) and "examples" in result:
            positive_examples = result["examples"]
            print(f"DEBUG: Generated {len(positive_examples)} positive examples")
        
        # Generate negative examples
        print(f"DEBUG: Generating {num_negative} negative examples...")
        result = generate_json(negative_prompt, temperature=0.8, task_type="generation", issue_hash=issue_hash)
        if isinstance(result, dict) and "examples" in result:
            negative_examples = result["examples"]
            print(f"DEBUG: Generated {len(negative_examples)} negative examples")
            
    except Exception as e:
        print(f"ERROR: Failed to generate training examples: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        "positive": positive_examples,
        "negative": negative_examples
    }


def generate_full_training_dataset(
    rules: List[Dict[str, Any]],
    issue_description: str,
    examples_per_rule: int = 50
) -> Dict[str, Any]:
    """
    Generate a full training dataset from multiple rules.
    
    Args:
        rules: List of accepted rules
        issue_description: The original issue description
        examples_per_rule: Number of examples to generate per rule (positive + negative)
        
    Returns:
        Dict with training data and metadata
    """
    print(f"DEBUG: Generating training dataset from {len(rules)} rules")
    
    issue_hash = hashlib.md5(issue_description.encode('utf-8')).hexdigest()
    
    all_positive = []
    all_negative = []
    
    num_positive_per_rule = examples_per_rule // 2
    num_negative_per_rule = examples_per_rule - num_positive_per_rule
    
    for i, rule in enumerate(rules):
        print(f"DEBUG: Processing rule {i+1}/{len(rules)}: {rule.get('title', 'Unknown')}")
        
        examples = generate_training_examples_from_rule(
            rule=rule,
            issue_description=issue_description,
            num_positive=num_positive_per_rule,
            num_negative=num_negative_per_rule,
            issue_hash=issue_hash
        )
        
        all_positive.extend(examples["positive"])
        all_negative.extend(examples["negative"])
    
    # Create dataset
    dataset = {
        "issue_description": issue_description,
        "issue_hash": issue_hash,
        "num_rules": len(rules),
        "train": [],
        "test": [],
        "metadata": {
            "total_positive": len(all_positive),
            "total_negative": len(all_negative),
            "rules_used": [r.get("title", "Unknown") for r in rules]
        }
    }
    
    # Split into train/test (80/20)
    import random
    random.seed(42)
    
    all_examples = []
    for ex in all_positive:
        all_examples.append({
            "user": ex.get("user", ""),
            "assistant": ex.get("assistant", ""),
            "label": 1  # MATCH
        })
    for ex in all_negative:
        all_examples.append({
            "user": ex.get("user", ""),
            "assistant": ex.get("assistant", ""),
            "label": 0  # NO_MATCH
        })
    
    random.shuffle(all_examples)
    
    split_idx = int(len(all_examples) * 0.8)
    dataset["train"] = all_examples[:split_idx]
    dataset["test"] = all_examples[split_idx:]
    
    print(f"DEBUG: Dataset created - Train: {len(dataset['train'])}, Test: {len(dataset['test'])}")
    
    return dataset


def save_dataset_to_huggingface_format(dataset: Dict[str, Any], output_dir: str) -> str:
    """
    Save dataset in HuggingFace datasets format.
    
    Args:
        dataset: The generated dataset
        output_dir: Directory to save the dataset
        
    Returns:
        Path to the saved dataset
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as JSONL files
    train_path = os.path.join(output_dir, "train.jsonl")
    test_path = os.path.join(output_dir, "test.jsonl")
    metadata_path = os.path.join(output_dir, "metadata.json")
    
    with open(train_path, 'w') as f:
        for example in dataset["train"]:
            # Combine user and assistant into a single text field
            text = f"User: {example['user']}\nAssistant: {example['assistant']}"
            f.write(json.dumps({"text": text, "label": example["label"]}) + "\n")
    
    with open(test_path, 'w') as f:
        for example in dataset["test"]:
            text = f"User: {example['user']}\nAssistant: {example['assistant']}"
            f.write(json.dumps({"text": text, "label": example["label"]}) + "\n")
    
    with open(metadata_path, 'w') as f:
        json.dump({
            "issue_description": dataset["issue_description"],
            "issue_hash": dataset["issue_hash"],
            "num_rules": dataset["num_rules"],
            "train_size": len(dataset["train"]),
            "test_size": len(dataset["test"]),
            "metadata": dataset["metadata"]
        }, f, indent=2)
    
    print(f"DEBUG: Dataset saved to {output_dir}")
    return output_dir

