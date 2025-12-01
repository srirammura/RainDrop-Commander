from typing import List, Dict, Any
from commander.services.gemini_client import generate_json
from commander.services.mock_audit_responses import get_mock_red_team_response


class RedTeamTool:
    def run(self, rule: str, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run red team analysis on the rule."""
        try:
            # Generate adversarial test cases
            positive_examples = [e for e in examples if e.get("label") == "MATCH"]
            negative_examples = [e for e in examples if e.get("label") == "NO_MATCH"]
            
            prompt = f"""You are creating test cases to validate a classification rule.

Rule Description: "{rule}"

Positive Examples (should match):
{chr(10).join(f'- "{e.get("text", "")}"' for e in positive_examples)}

Negative Examples (should not match):
{chr(10).join(f'- "{e.get("text", "")}"' for e in negative_examples) if negative_examples else "None provided"}

Generate 10 test cases that explore different scenarios and boundary conditions. Include variations that are semantically similar but might behave differently, or cases that test the rule's boundaries.

Return a JSON object with this structure:
{{
  "test_cases": [
    {{
      "text": "the test case text",
      "should_match": true or false,
      "reasoning": "why this tests the rule boundary"
    }}
  ]
}}"""

            # Test case generation is moderate analysis - use medium effort
            adversarial_cases, _ = generate_json(prompt, task_type="test_generation")

            # Analyze which test cases would actually trigger the rule
            analysis_prompt = f"""Evaluate if these test cases would match the rule: "{rule}"

Test Cases:
{chr(10).join(f'{i+1}. "{tc.get("text", "")}" (expected_match: {tc.get("should_match", False)})' for i, tc in enumerate(adversarial_cases.get("test_cases", [])))}

For each test case, determine if it would actually match the rule based on the rule description and the examples provided.

Return a JSON object:
{{
  "results": [
    {{
      "test_case": "the test case text",
      "would_match": true or false,
      "should_match": true or false,
      "is_problematic": true if would_match != should_match
    }}
  ],
  "robustness_score": number between 0-100 (100 = all test cases behave correctly)
}}"""

            # Test case analysis is moderate - use medium effort
            analysis, _ = generate_json(analysis_prompt, task_type="analysis")

            problematic_cases = [r for r in analysis.get("results", []) if r.get("is_problematic", False)]
            score = analysis.get("robustness_score", 0)

            if score < 60:
                return {
                    "tool_name": "Synthetic Red Team",
                    "status": "FAIL",
                    "message": f"Rule fails on {len(problematic_cases)} edge case tests. Robustness score: {score}/100. Rule triggers on inputs that should not match.",
                    "score": score,
                    "details": {
                        "adversarial_cases": [r.get("test_case") for r in problematic_cases],
                    },
                }
            elif score < 80:
                return {
                    "tool_name": "Synthetic Red Team",
                    "status": "WARN",
                    "message": f"Rule may trigger on {len(problematic_cases)} edge cases. Robustness score: {score}/100. Consider adding negative constraints.",
                    "score": score,
                    "details": {
                        "adversarial_cases": [r.get("test_case") for r in problematic_cases],
                    },
                }
            else:
                return {
                    "tool_name": "Synthetic Red Team",
                    "status": "PASS",
                    "message": f"Rule is robust against edge case testing. Robustness score: {score}/100.",
                    "score": score,
                }
        except Exception as error:
            error_msg = str(error)
            # If blocked by safety filters, use mock response
            if "SAFETY" in error_msg.upper() or "blocked" in error_msg.lower() or "finish_reason" in error_msg.lower():
                return get_mock_red_team_response(rule, examples)
            return {
                "tool_name": "Synthetic Red Team",
                "status": "WARN",
                "message": f"Error during red team analysis: {error_msg}",
            }

