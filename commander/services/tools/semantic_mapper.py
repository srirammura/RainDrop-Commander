from typing import List, Dict, Any
from commander.services.gemini_client import generate_json
from commander.services.mock_audit_responses import get_mock_semantic_mapper_response


class SemanticMapperTool:
    def run(self, rule: str, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run semantic boundary mapping on the rule with quality analysis."""
        try:
            positive_examples = [e for e in examples if e.get("label") == "MATCH" or e.get("user_label") == "MATCH"]
            negative_examples = [e for e in examples if e.get("label") == "NO_MATCH" or e.get("user_label") == "NO_MATCH"]
            
            # Quality Check 1: Insufficient examples
            if len(positive_examples) < 2:
                return {
                    "tool_name": "Semantic Boundary Mapper",
                    "status": "WARN",
                    "message": f"Insufficient positive examples ({len(positive_examples)}). Need at least 2 positive examples to map rule boundaries effectively.",
                    "details": {
                        "issue": "insufficient_examples",
                        "positive_count": len(positive_examples),
                        "negative_count": len(negative_examples),
                    },
                }
            
            if len(negative_examples) < 2:
                return {
                    "tool_name": "Semantic Boundary Mapper",
                    "status": "WARN",
                    "message": f"Insufficient negative examples ({len(negative_examples)}). Need at least 2 negative examples to map rule boundaries effectively.",
                    "details": {
                        "issue": "insufficient_examples",
                        "positive_count": len(positive_examples),
                        "negative_count": len(negative_examples),
                    },
                }
            
            # Enhanced prompt with quality analysis
            prompt = f"""You are analyzing classification rule boundaries and evaluating rule quality.

Rule Description: "{rule}"

Positive Examples (should match):
{chr(10).join(f'- "{e.get("user", "")} / {e.get("assistant", "")}"' if "user" in e else f'- "{e.get("text", "")}"' for e in positive_examples[:10])}

Negative Examples (should not match):
{chr(10).join(f'- "{e.get("user", "")} / {e.get("assistant", "")}"' if "user" in e else f'- "{e.get("text", "")}"' for e in negative_examples[:10]) if negative_examples else "None provided"}

YOUR TASK:
1. Analyze the rule and examples for boundary clarity
2. Generate boundary examples
3. Evaluate rule quality

QUALITY ANALYSIS REQUIRED:
- Rule Clarity: Is the rule specific enough? Can you clearly identify what should match vs not match?
- Example Consistency: Do the examples consistently support the rule? Are there contradictions?
- Boundary Definition: Can you identify clear boundaries between matches and non-matches?
- Rule Scope: Is the rule too broad (matches too much) or too narrow (matches too little)?

Generate:
1. 5 examples that are close to the boundary but should match (edge cases)
2. 5 examples that are close to the boundary but should not match

Return a JSON object:
{{
  "quality_analysis": {{
    "rule_clarity": "clear|unclear|ambiguous",
    "example_consistency": "consistent|some_contradictions|highly_contradictory",
    "boundary_definition": "well_defined|somewhat_defined|poorly_defined",
    "rule_scope": "appropriate|too_broad|too_narrow",
    "overall_assessment": "good|needs_refinement|poor",
    "issues_found": ["list of specific issues if any"],
    "recommendations": ["list of recommendations for improvement"]
  }},
  "examples_inside": [
    {{
      "text": "example text",
      "reasoning": "why this should match"
    }}
  ],
  "examples_outside": [
    {{
      "text": "example text",
      "reasoning": "why this should not match"
    }}
  ]
}}"""

            # Boundary mapping with quality analysis is complex - use high effort
            boundary_result, _ = generate_json(prompt, temperature=0.5, task_type="boundary_mapping")
            
            # Extract quality analysis
            quality = boundary_result.get("quality_analysis", {})
            overall_assessment = quality.get("overall_assessment", "good")
            issues_found = quality.get("issues_found", [])
            rule_clarity = quality.get("rule_clarity", "clear")
            boundary_definition = quality.get("boundary_definition", "well_defined")
            
            # Determine status based on quality analysis
            status = "PASS"
            message_parts = []
            
            # Quality Check 2: Unclear rule boundaries
            if rule_clarity in ["unclear", "ambiguous"]:
                status = "WARN"
                message_parts.append("Rule boundaries are unclear or ambiguous.")
            
            # Quality Check 3: Poor boundary definition
            if boundary_definition == "poorly_defined":
                status = "WARN"
                message_parts.append("Rule boundaries are poorly defined.")
            
            # Quality Check 4: Contradictory examples
            example_consistency = quality.get("example_consistency", "consistent")
            if example_consistency in ["some_contradictions", "highly_contradictory"]:
                status = "WARN"
                message_parts.append("Examples show contradictions that make boundaries unclear.")
            
            # Quality Check 5: Rule too broad or narrow
            rule_scope = quality.get("rule_scope", "appropriate")
            if rule_scope in ["too_broad", "too_narrow"]:
                status = "WARN"
                if rule_scope == "too_broad":
                    message_parts.append("Rule is too broad and may match unintended cases.")
                else:
                    message_parts.append("Rule is too narrow and may miss valid cases.")
            
            # Overall assessment
            if overall_assessment == "poor":
                status = "WARN"
                message_parts.append("Overall rule quality is poor and needs significant refinement.")
            elif overall_assessment == "needs_refinement":
                if status == "PASS":
                    status = "WARN"
                message_parts.append("Rule needs refinement for better boundary clarity.")
            
            # Build message
            if message_parts:
                quality_message = " ".join(message_parts)
                if issues_found:
                    quality_message += f" Issues: {', '.join(issues_found[:3])}."
            else:
                quality_message = "Rule boundaries are well-defined and clear."
            
            examples_inside = boundary_result.get("examples_inside", [])
            examples_outside = boundary_result.get("examples_outside", [])
            
            full_message = f"Generated {len(examples_inside)} boundary examples inside and {len(examples_outside)} outside the rule. {quality_message}"
            
            return {
                "tool_name": "Semantic Boundary Mapper",
                "status": status,
                "message": full_message,
                "details": {
                    "boundary_examples_inside": [e.get("text") for e in examples_inside],
                    "boundary_examples_outside": [e.get("text") for e in examples_outside],
                    "quality_analysis": quality,
                },
            }
        except Exception as error:
            error_msg = str(error)
            # If blocked by safety filters, use mock response
            if "SAFETY" in error_msg.upper() or "blocked" in error_msg.lower() or "finish_reason" in error_msg.lower():
                return get_mock_semantic_mapper_response(rule, examples)
            return {
                "tool_name": "Semantic Boundary Mapper",
                "status": "WARN",
                "message": f"Error during semantic mapping: {error_msg}",
            }
