"""Service to scan WildChat dataset at scale using trained classifier."""
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
import json
import os
import time


def scan_wildchat_with_classifier(
    model_dir: str,
    issue_description: str,
    num_samples: int = 10000,
    batch_size: int = 64,
    confidence_threshold: float = 0.7,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Scan WildChat dataset using trained classifier to find issue occurrences.
    
    Args:
        model_dir: Directory containing the trained model
        issue_description: The issue we're looking for
        num_samples: Number of samples to scan
        batch_size: Batch size for inference
        confidence_threshold: Minimum confidence to flag as issue
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dict with scan results and flagged conversations
    """
    from commander.services.dataset_service import _load_wildchat_dataset, _extract_conversation_from_wildchat
    from commander.services.classifier_trainer import load_classifier, predict_batch
    
    print(f"DEBUG: Starting scan of {num_samples:,} WildChat examples")
    print(f"DEBUG: Looking for: {issue_description[:50]}...")
    
    start_time = time.time()
    
    # Load classifier
    print("DEBUG: Loading classifier...")
    model, tokenizer = load_classifier(model_dir)
    
    # Load dataset
    print("DEBUG: Loading WildChat dataset...")
    dataset, dataset_size = _load_wildchat_dataset()
    
    # Sample indices
    import random
    sample_indices = random.sample(range(dataset_size), min(num_samples, dataset_size))
    
    # Prepare texts for classification
    print("DEBUG: Extracting conversations...")
    texts = []
    conversations = []
    
    for i, idx in enumerate(sample_indices):
        try:
            example = dataset[idx]
            conv = _extract_conversation_from_wildchat(example)
            
            if conv:
                text = f"User: {conv['user']}\nAssistant: {conv['assistant']}"
                texts.append(text)
                conversations.append({
                    "index": idx,
                    "user": conv["user"],
                    "assistant": conv["assistant"]
                })
        except Exception as e:
            continue
        
        if progress_callback and i % 1000 == 0:
            progress_callback({"phase": "extracting", "progress": i / len(sample_indices)})
    
    print(f"DEBUG: Extracted {len(texts)} valid conversations")
    
    # Run classification
    print(f"DEBUG: Running classifier on {len(texts)} texts...")
    
    flagged_issues = []
    total_matches = 0
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_convs = conversations[i:i+batch_size]
        
        predictions = predict_batch(model, tokenizer, batch_texts, batch_size=batch_size)
        
        for j, (pred, conv) in enumerate(zip(predictions, batch_convs)):
            if pred["prediction"] == "MATCH" and pred["confidence"] >= confidence_threshold:
                total_matches += 1
                flagged_issues.append({
                    "id": f"issue_{total_matches}",
                    "dataset_index": conv["index"],
                    "user": conv["user"][:500],  # Truncate for storage
                    "assistant": conv["assistant"][:500],
                    "confidence": pred["confidence"],
                    "probabilities": pred["probabilities"]
                })
        
        if progress_callback and i % (batch_size * 10) == 0:
            progress_callback({
                "phase": "classifying",
                "progress": i / len(texts),
                "matches_found": total_matches
            })
    
    end_time = time.time()
    scan_duration = end_time - start_time
    
    # Calculate metrics
    scan_rate = len(texts) / scan_duration if scan_duration > 0 else 0
    issue_rate = total_matches / len(texts) * 100 if len(texts) > 0 else 0
    
    # Sort by confidence
    flagged_issues.sort(key=lambda x: x["confidence"], reverse=True)
    
    results = {
        "issue_description": issue_description,
        "scan_timestamp": datetime.now().isoformat(),
        "total_scanned": len(texts),
        "total_flagged": total_matches,
        "issue_rate_percent": round(issue_rate, 2),
        "scan_duration_seconds": round(scan_duration, 2),
        "scan_rate_per_second": round(scan_rate, 1),
        "confidence_threshold": confidence_threshold,
        "flagged_issues": flagged_issues[:100],  # Top 100 for display
        "metrics": {
            "high_confidence": len([x for x in flagged_issues if x["confidence"] >= 0.9]),
            "medium_confidence": len([x for x in flagged_issues if 0.7 <= x["confidence"] < 0.9]),
            "avg_confidence": sum(x["confidence"] for x in flagged_issues) / len(flagged_issues) if flagged_issues else 0
        }
    }
    
    print(f"DEBUG: Scan complete!")
    print(f"DEBUG: Scanned {len(texts):,} examples in {scan_duration:.1f}s ({scan_rate:.0f}/sec)")
    print(f"DEBUG: Found {total_matches:,} issues ({issue_rate:.2f}%)")
    
    return results


def save_scan_results(results: Dict[str, Any], output_dir: str) -> str:
    """
    Save scan results to disk.
    
    Args:
        results: Scan results dict
        output_dir: Directory to save results
        
    Returns:
        Path to saved results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save full results
    results_path = os.path.join(output_dir, "scan_results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save summary
    summary_path = os.path.join(output_dir, "scan_summary.json")
    summary = {k: v for k, v in results.items() if k != "flagged_issues"}
    summary["num_flagged_saved"] = len(results.get("flagged_issues", []))
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"DEBUG: Results saved to {output_dir}")
    return results_path


def get_issue_drilldown(results: Dict[str, Any], issue_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed view of a flagged issue.
    
    Args:
        results: Scan results
        issue_id: ID of the issue to drill down
        
    Returns:
        Issue details or None if not found
    """
    for issue in results.get("flagged_issues", []):
        if issue.get("id") == issue_id:
            return issue
    return None


def get_scan_statistics(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate detailed statistics from scan results.
    
    Args:
        results: Scan results
        
    Returns:
        Statistics dict
    """
    flagged = results.get("flagged_issues", [])
    
    if not flagged:
        return {
            "total_flagged": 0,
            "confidence_distribution": {},
            "estimated_in_full_dataset": 0
        }
    
    # Confidence distribution
    conf_buckets = {
        "0.9-1.0": 0,
        "0.8-0.9": 0,
        "0.7-0.8": 0,
        "<0.7": 0
    }
    
    for issue in flagged:
        conf = issue.get("confidence", 0)
        if conf >= 0.9:
            conf_buckets["0.9-1.0"] += 1
        elif conf >= 0.8:
            conf_buckets["0.8-0.9"] += 1
        elif conf >= 0.7:
            conf_buckets["0.7-0.8"] += 1
        else:
            conf_buckets["<0.7"] += 1
    
    # Estimate in full dataset
    issue_rate = results.get("issue_rate_percent", 0)
    estimated_full = int(1000000 * issue_rate / 100)  # Assuming 1M total conversations
    
    return {
        "total_flagged": len(flagged),
        "confidence_distribution": conf_buckets,
        "avg_confidence": results.get("metrics", {}).get("avg_confidence", 0),
        "issue_rate_percent": issue_rate,
        "estimated_in_full_dataset": estimated_full,
        "scan_rate": results.get("scan_rate_per_second", 0)
    }

