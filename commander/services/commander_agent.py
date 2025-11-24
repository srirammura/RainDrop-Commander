from typing import List, Dict, Any
from datetime import datetime
from commander.services.tools.red_team_tool import RedTeamTool
from commander.services.tools.overfit_detector import OverfitDetectorTool
from commander.services.tools.semantic_mapper import SemanticMapperTool
from commander.services.gemini_client import generate_text


class CommanderAgent:
    def __init__(self, rule_description: str, examples: List[Dict[str, Any]]):
        self.rule = rule_description
        self.examples = examples
        self.tools = [
            RedTeamTool(),
            OverfitDetectorTool(),
            SemanticMapperTool(),
        ]

    def audit_rule(self) -> Dict[str, Any]:
        """Audit the rule using all tools."""
        print(f"👮 COMMANDER: Auditing rule '{self.rule}'...")

        reports = []

        # Run all tools sequentially
        for tool in self.tools:
            tool_name = tool.__class__.__name__
            print(f"   ↳ Running {tool_name}...")
            
            try:
                report = tool.run(self.rule, self.examples)
                reports.append(report)
            except Exception as error:
                print(f"Error running {tool_name}: {error}")
                reports.append({
                    "tool_name": tool_name,
                    "status": "WARN",
                    "message": f"Error: {str(error)}",
                })

        # Synthesize executive summary
        executive_summary = self._generate_executive_summary(reports)

        return {
            "rule_description": self.rule,
            "examples": self.examples,
            "reports": reports,
            "executive_summary": executive_summary,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_executive_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate executive summary from tool reports with weighted scoring."""
        critical_issues = [r for r in reports if r.get("status") == "FAIL"]
        warnings = [r for r in reports if r.get("status") == "WARN"]
        passes = [r for r in reports if r.get("status") == "PASS"]

        # Extract scores from reports
        overfit_score = None
        red_team_score = None
        boundary_status = None
        
        for report in reports:
            if report.get("tool_name") == "Variance/Overfit Detector":
                # Try multiple fields for overfit score
                overfit_score = report.get("score") or report.get("variance_score")
                if overfit_score is None and "details" in report:
                    overfit_score = report.get("details", {}).get("variance_score")
            elif report.get("tool_name") == "Synthetic Red Team":
                red_team_score = report.get("score")
            elif report.get("tool_name") == "Semantic Boundary Mapper":
                boundary_status = report.get("status", "PASS")
        
        # Calculate weighted cumulative score
        # Overfit score has highest weight (60%), Red Team (30%), Boundary (10%)
        cumulative_score = 0
        weights_applied = 0
        
        if overfit_score is not None:
            cumulative_score += overfit_score * 0.6
            weights_applied += 0.6
        else:
            # If overfit score missing, penalize heavily
            cumulative_score += 30 * 0.6  # Low score assumption
            weights_applied += 0.6
        
        if red_team_score is not None:
            cumulative_score += red_team_score * 0.3
            weights_applied += 0.3
        else:
            # If red team score missing, use status-based score
            red_team_status_score = 50 if warnings else (30 if critical_issues else 80)
            cumulative_score += red_team_status_score * 0.3
            weights_applied += 0.3
        
        # Boundary mapping contributes 10%
        boundary_score = 100 if boundary_status == "PASS" else (50 if boundary_status == "WARN" else 30)
        cumulative_score += boundary_score * 0.1
        weights_applied += 0.1
        
        # Normalize if weights don't sum to 1.0
        if weights_applied > 0:
            cumulative_score = cumulative_score / weights_applied
        
        # Determine overall status and recommendation based on weighted score
        if len(critical_issues) > 0 or cumulative_score < 50:
            overall_status = "REJECTED"
            recommendation = "❌ NOT RECOMMENDED: This rule has critical issues or low overall score. Review the detailed scores before deploying."
        elif cumulative_score < 70 or (overfit_score is not None and overfit_score < 60):
            overall_status = "APPROVED_WITH_WARNINGS"
            recommendation = "⚠️ PROCEED WITH CAUTION: This rule may have generalization issues. Consider reviewing the overfit score and adding more diverse examples."
        else:
            overall_status = "APPROVED"
            recommendation = "✅ RECOMMENDED: This rule shows good generalization and robustness. Safe to deploy."

        # Add score-based recommendation if needed
        if overfit_score is not None and overfit_score < 50:
            recommendation = "❌ NOT RECOMMENDED: Low overfit score indicates poor generalization. This rule may fail on new examples."
        elif overfit_score is not None and overfit_score >= 80 and cumulative_score >= 75:
            recommendation = "✅ STRONGLY RECOMMENDED: High overfit score and good overall performance. This rule should generalize well."

        return {
            "overall_status": overall_status,
            "critical_issues_count": len(critical_issues),
            "warnings_count": len(warnings),
            "recommendation": recommendation,
            "cumulative_score": round(cumulative_score, 1),
            "overfit_score": overfit_score,
            "red_team_score": red_team_score,
            "boundary_status": boundary_status,
        }

