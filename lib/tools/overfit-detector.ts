import { ToolReport, Example } from "../types";
import { generateText, generateJSON } from "../gemini-client";

interface OverfitAnalysis {
  is_overfit: boolean;
  detected_patterns: string[];
  narrow_terms: string[];
  variance_score: number; // 0-100, higher = more variance
  recommendation: string;
}

export class OverfitDetectorTool {
  async run(rule: string, examples: Example[]): Promise<ToolReport> {
    try {
      const positiveExamples = examples.filter(e => e.label === "MATCH");
      
      if (positiveExamples.length < 2) {
        return {
          tool_name: "Variance/Overfit Detector",
          status: "WARN",
          message: "Insufficient positive examples to detect overfitting. Provide at least 2-3 examples.",
        };
      }

      const prompt = `Analyze these training examples for potential overfitting.

Rule Description: "${rule}"

Positive Examples (should match):
${positiveExamples.map(e => `- "${e.text}"`).join("\n")}

Analyze:
1. Do all examples share specific proper nouns, brand names, or narrow terms that aren't in the rule description?
2. Is the rule description broader than what the examples suggest?
3. Would the rule fail on similar cases that don't use the same specific terms?

Return a JSON object:
{
  "is_overfit": true or false,
  "detected_patterns": ["pattern1", "pattern2"],
  "narrow_terms": ["term1", "term2"],
  "variance_score": number 0-100 (100 = high variance, good),
  "recommendation": "specific recommendation"
}`;

      const analysis = await generateJSON<OverfitAnalysis>(prompt);

      if (analysis.is_overfit || analysis.variance_score < 40) {
        return {
          tool_name: "Variance/Overfit Detector",
          status: "WARN",
          message: `Examples are too narrow. Detected patterns: ${analysis.detected_patterns.join(", ")}. Variance score: ${analysis.variance_score}/100. ${analysis.recommendation}`,
          details: {
            detected_patterns: analysis.detected_patterns,
          },
        };
      } else if (analysis.variance_score < 60) {
        return {
          tool_name: "Variance/Overfit Detector",
          status: "WARN",
          message: `Examples show limited variance. Consider adding examples with different terms. Variance score: ${analysis.variance_score}/100.`,
          details: {
            detected_patterns: analysis.detected_patterns,
          },
        };
      } else {
        return {
          tool_name: "Variance/Overfit Detector",
          status: "PASS",
          message: `Examples show good variance. Variance score: ${analysis.variance_score}/100.`,
        };
      }
    } catch (error) {
      console.error("Overfit Detector error:", error);
      return {
        tool_name: "Variance/Overfit Detector",
        status: "WARN",
        message: `Error during overfit detection: ${error instanceof Error ? error.message : "Unknown error"}`,
      };
    }
  }
}

