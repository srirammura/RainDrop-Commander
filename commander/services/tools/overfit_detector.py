from typing import List, Dict, Any
from commander.services.gemini_client import generate_json
from commander.services.mock_audit_responses import get_mock_overfit_detector_response


class OverfitDetectorTool:
    def run(self, rule: str, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run overfit detection analysis on the rule."""
        try:
            positive_examples = [e for e in examples if e.get("label") == "MATCH"]
            
            if len(positive_examples) < 2:
                return {
                    "tool_name": "Variance/Overfit Detector",
                    "status": "WARN",
                    "message": "Insufficient positive examples to detect overfitting. Provide at least 2-3 examples.",
                }

            prompt = f"""Analyze these training examples for potential overfitting.

Rule Description: "{rule}"

Positive Examples (should match):
{chr(10).join(f'- "{e.get("text", "")}"' for e in positive_examples)}

Analyze:
1. Do all examples share specific proper nouns, brand names, or narrow terms that aren't in the rule description?
2. Is the rule description broader than what the examples suggest?
3. Would the rule fail on similar cases that don't use the same specific terms?

Return a JSON object:
{{
  "is_overfit": true or false,
  "detected_patterns": ["pattern1", "pattern2"],
  "narrow_terms": ["term1", "term2"],
  "variance_score": number 0-100 (100 = high variance, good),
  "recommendation": "specific recommendation"
}}"""

            # Overfit detection is moderate analysis - use medium effort
            analysis, _ = generate_json(prompt, task_type="overfit_detection")

            variance_score = analysis.get("variance_score", 0)
            if analysis.get("is_overfit") or variance_score < 40:
                return {
                    "tool_name": "Variance/Overfit Detector",
                    "status": "WARN",
                    "message": f"Examples are too narrow. Detected patterns: {', '.join(analysis.get('detected_patterns', []))}. Variance score: {variance_score}/100. {analysis.get('recommendation', '')}",
                    "score": variance_score,  # Add score field for display
                    "details": {
                        "detected_patterns": analysis.get("detected_patterns", []),
                        "variance_score": variance_score,
                    },
                }
            elif variance_score < 60:
                return {
                    "tool_name": "Variance/Overfit Detector",
                    "status": "WARN",
                    "message": f"Examples show limited variance. Consider adding examples with different terms. Variance score: {variance_score}/100.",
                    "score": variance_score,  # Add score field for display
                    "details": {
                        "detected_patterns": analysis.get("detected_patterns", []),
                        "variance_score": variance_score,
                    },
                }
            else:
                return {
                    "tool_name": "Variance/Overfit Detector",
                    "status": "PASS",
                    "message": f"Examples show good variance. Variance score: {variance_score}/100.",
                    "score": variance_score,  # Add score field for display
                    "details": {
                        "variance_score": variance_score,
                    },
                }
        except Exception as error:
            error_msg = str(error)
            # If blocked by safety filters, use mock response
            if "SAFETY" in error_msg.upper() or "blocked" in error_msg.lower() or "finish_reason" in error_msg.lower():
                return get_mock_overfit_detector_response(rule, examples)
            return {
                "tool_name": "Variance/Overfit Detector",
                "status": "WARN",
                "message": f"Error during overfit detection: {error_msg}",
            }

