"""
Adaptive Routing Supervisor Agent for intelligent effort level determination.
Uses hybrid approach: rule-based for simple cases, LLM for ambiguous ones.
"""
import os
import re
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv
from commander.services.gemini_client import generate_json
from commander.services.effort_config import EffortLevel, get_effort_level

load_dotenv()

# Configuration
ROUTING_SUPERVISOR_ENABLED = os.getenv("ROUTING_SUPERVISOR_ENABLED", "true").lower() == "true"
ROUTING_LLM_THRESHOLD = float(os.getenv("ROUTING_LLM_THRESHOLD", "0.7"))  # Confidence threshold for LLM routing

# Complexity keywords that suggest high effort
HIGH_EFFORT_KEYWORDS = [
    "analyze", "synthesize", "reason", "complex", "multiple", "comprehensive",
    "detailed", "thorough", "evaluate", "assess", "compare", "contrast",
    "boundary", "edge case", "quality", "robustness", "generalization"
]

# Simple keywords that suggest low effort
LOW_EFFORT_KEYWORDS = [
    "validate", "check", "verify", "confirm", "yes", "no", "classify",
    "categorize", "simple", "basic", "straightforward"
]


def analyze_prompt_complexity(prompt: str, task_type: str) -> Dict[str, any]:
    """
    Rule-based analysis of prompt complexity.
    
    Returns:
        dict with 'effort', 'confidence', 'reasoning'
    """
    prompt_lower = prompt.lower()
    prompt_length = len(prompt)
    word_count = len(prompt.split())
    
    # Count complexity indicators
    high_effort_count = sum(1 for keyword in HIGH_EFFORT_KEYWORDS if keyword in prompt_lower)
    low_effort_count = sum(1 for keyword in LOW_EFFORT_KEYWORDS if keyword in prompt_lower)
    
    # Rule-based decision logic
    effort = "medium"  # Default
    confidence = 0.5
    reasoning_parts = []
    
    # Length-based heuristics
    if prompt_length < 200:
        effort = "low"
        confidence = 0.7
        reasoning_parts.append("Short prompt suggests simple task")
    elif prompt_length > 2000:
        effort = "high"
        confidence = 0.7
        reasoning_parts.append("Long prompt suggests complex task")
    
    # Keyword-based heuristics
    if high_effort_count > low_effort_count + 2:
        effort = "high"
        confidence = min(0.9, confidence + 0.2)
        reasoning_parts.append(f"Found {high_effort_count} high-complexity keywords")
    elif low_effort_count > high_effort_count + 2:
        effort = "low"
        confidence = min(0.9, confidence + 0.2)
        reasoning_parts.append(f"Found {low_effort_count} low-complexity keywords")
    
    # Task type override
    task_type_effort = get_effort_level(task_type)
    if task_type_effort in ["high"] and effort == "low":
        effort = "medium"  # Upgrade if task type suggests higher effort
        confidence = 0.6
        reasoning_parts.append(f"Task type '{task_type}' suggests higher effort")
    elif task_type_effort in ["low"] and effort == "high":
        effort = "medium"  # Downgrade if task type suggests lower effort
        confidence = 0.6
        reasoning_parts.append(f"Task type '{task_type}' suggests lower effort")
    
    reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Rule-based analysis"
    
    return {
        "effort": effort,
        "confidence": confidence,
        "reasoning": reasoning,
        "method": "rule_based"
    }


def route_with_llm(prompt: str, task_type: str) -> Dict[str, any]:
    """
    Use LLM to determine effort level for ambiguous cases.
    
    Returns:
        dict with 'effort', 'confidence', 'reasoning'
    """
    routing_prompt = f"""Analyze this task and determine the appropriate thinking effort level needed.

Task Type: {task_type}
Task Description/Prompt (first 500 chars): {prompt[:500]}

Consider:
- Low effort: Simple validation, classification, straightforward tasks
- Medium effort: Content generation, moderate analysis, standard processing
- High effort: Complex reasoning, synthesis, boundary analysis, comprehensive evaluation

Return JSON with:
{{
  "effort": "low" or "medium" or "high",
  "reasoning": "Brief explanation of why this effort level is appropriate"
}}"""

    try:
        # Use low effort for the routing call itself to save costs
        result = generate_json(routing_prompt, temperature=0.3, task_type="classification", effort="low")
        
        effort = result.get("effort", "medium").lower()
        if effort not in ["low", "medium", "high"]:
            effort = "medium"
        
        return {
            "effort": effort,
            "confidence": 0.85,  # High confidence for LLM decisions
            "reasoning": result.get("reasoning", "LLM-based routing decision"),
            "method": "llm_based"
        }
    except Exception as e:
        # Fallback to rule-based if LLM fails
        print(f"WARNING: LLM routing failed, using rule-based fallback: {e}")
        return analyze_prompt_complexity(prompt, task_type)


def route_effort_level(prompt: str, task_type: str = "analysis") -> Tuple[EffortLevel, Dict[str, any]]:
    """
    Adaptive routing supervisor: determines optimal effort level.
    
    Uses hybrid approach:
    1. Rule-based analysis first (fast, no cost)
    2. LLM routing if confidence is below threshold (intelligent, low cost)
    
    Args:
        prompt: The prompt or task description
        task_type: Type of task (for context)
    
    Returns:
        Tuple of (effort_level, routing_info)
        routing_info contains: effort, confidence, reasoning, method
    """
    if not ROUTING_SUPERVISOR_ENABLED:
        # Fallback to existing logic
        effort = get_effort_level(task_type)
        return effort, {
            "effort": effort,
            "confidence": 0.5,
            "reasoning": "Routing supervisor disabled, using task_type mapping",
            "method": "fallback"
        }
    
    # Step 1: Rule-based analysis
    rule_analysis = analyze_prompt_complexity(prompt, task_type)
    confidence = rule_analysis["confidence"]
    
    # Step 2: Use LLM if confidence is below threshold
    if confidence < ROUTING_LLM_THRESHOLD:
        print(f"DEBUG: Routing confidence ({confidence}) below threshold ({ROUTING_LLM_THRESHOLD}), using LLM routing")
        llm_analysis = route_with_llm(prompt, task_type)
        return llm_analysis["effort"], llm_analysis
    else:
        print(f"DEBUG: Routing confidence ({confidence}) sufficient, using rule-based decision: {rule_analysis['effort']}")
        return rule_analysis["effort"], rule_analysis

