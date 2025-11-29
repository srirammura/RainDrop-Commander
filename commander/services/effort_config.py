"""
Effort parameter configuration and utilities for Claude Opus 4.5.
Controls token usage to reduce costs by 50-80% on simple tasks.
"""
import os
import logging
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Environment variable configuration
EFFORT_ENABLED = os.getenv("CLAUDE_EFFORT_ENABLED", "true").lower() == "true"
EFFORT_DEFAULT = os.getenv("CLAUDE_EFFORT_DEFAULT", "medium").lower()
EFFORT_HEADER = "anthropic-beta-effort-2025-11-24"

# Effort level type
EffortLevel = Literal["low", "medium", "high"]

# Statistics tracking
_effort_stats = {
    "low": 0,
    "medium": 0,
    "high": 0,
    "fallback": 0,
}


def get_effort_level(task_type: str, override: str = None) -> EffortLevel:
    """
    Determine appropriate effort level based on task type.
    
    Args:
        task_type: Type of task being performed
        override: Optional override effort level (from env or explicit)
    
    Returns:
        "low", "medium", or "high"
    
    Task Types:
    - "validation": Simple yes/no, classification - "low"
    - "classification": Simple categorization - "low"
    - "generation": Content generation - "medium"
    - "analysis": Moderate analysis tasks - "medium"
    - "synthesis": Complex rule/pattern synthesis - "high"
    - "reasoning": Deep reasoning, executive summaries - "high"
    - "boundary_mapping": Complex boundary analysis - "high"
    """
    if not EFFORT_ENABLED:
        return "high"  # Default to high if effort feature disabled
    
    # Check for override
    if override:
        effort = override.lower()
        if effort in ["low", "medium", "high"]:
            return effort
    
    # Map task types to effort levels
    task_type_lower = task_type.lower()
    
    # Low effort: Simple validation, classification
    if task_type_lower in ["validation", "classification", "simple_check"]:
        return "low"
    
    # Medium effort: Generation, moderate analysis
    if task_type_lower in ["generation", "analysis", "test_generation", "overfit_detection"]:
        return "medium"
    
    # High effort: Complex reasoning, synthesis, boundary mapping
    if task_type_lower in ["synthesis", "reasoning", "boundary_mapping", "executive_summary", "rule_generation"]:
        return "high"
    
    # Default to medium if task type unknown
    return EFFORT_DEFAULT if EFFORT_DEFAULT in ["low", "medium", "high"] else "medium"


def get_effort_headers(effort_level: EffortLevel) -> dict:
    """
    Get HTTP headers for effort parameter.
    
    Args:
        effort_level: "low", "medium", or "high"
    
    Returns:
        Dictionary with headers, or empty dict if effort disabled
    """
    if not EFFORT_ENABLED:
        return {}
    
    return {
        EFFORT_HEADER: effort_level
    }


def log_effort_usage(effort_level: EffortLevel, task_type: str = "unknown"):
    """Log effort level usage for cost tracking."""
    if EFFORT_ENABLED:
        _effort_stats[effort_level] = _effort_stats.get(effort_level, 0) + 1
        logger.info(f"Effort level used: {effort_level} for task: {task_type}")
        print(f"DEBUG: Using effort level '{effort_level}' for task: {task_type}")


def get_effort_statistics() -> dict:
    """Get statistics on effort level usage."""
    total = sum(_effort_stats.values())
    if total == 0:
        return {"total": 0, "breakdown": {}}
    
    return {
        "total": total,
        "breakdown": _effort_stats.copy(),
        "percentages": {
            level: (count / total * 100) if total > 0 else 0
            for level, count in _effort_stats.items()
        }
    }


def reset_effort_statistics():
    """Reset effort statistics (useful for testing)."""
    global _effort_stats
    _effort_stats = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "fallback": 0,
    }

