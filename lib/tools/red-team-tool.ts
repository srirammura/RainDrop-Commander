import { ToolReport, Example } from "../types";
import { generateText, generateJSON } from "../gemini-client";

interface AdversarialTestCases {
  test_cases: Array<{
    text: string;
    should_match: boolean;
    reasoning: string;
  }>;
}

export class RedTeamTool {
  async run(rule: string, examples: Example[]): Promise<ToolReport> {
    try {
      // Generate adversarial test cases
      const prompt = `You are a red team agent testing a rule for robustness.

Rule Description: "${rule}"

Positive Examples (should match):
${examples.filter(e => e.label === "MATCH").map(e => `- "${e.text}"`).join("\n")}

Negative Examples (should not match):
${examples.filter(e => e.label === "NO_MATCH").map(e => `- "${e.text}"`).join("\n") || "None provided"}

Generate 10 adversarial test cases that might cause false positives or false negatives. These should be edge cases, ambiguous inputs, or inputs that are semantically similar but should not match (or vice versa).

Return a JSON object with this structure:
{
  "test_cases": [
    {
      "text": "the test case text",
      "should_match": true or false,
      "reasoning": "why this might be problematic"
    }
  ]
}`;

      const adversarialCases = await generateJSON<AdversarialTestCases>(prompt);

      // Analyze which test cases would actually trigger the rule
      const analysisPrompt = `Analyze if these test cases would match the rule: "${rule}"

Test Cases:
${adversarialCases.test_cases.map((tc, i) => `${i + 1}. "${tc.text}" (should_match: ${tc.should_match})`).join("\n")}

For each test case, determine if it would actually match the rule based on the rule description and the examples provided.

Return a JSON object:
{
  "results": [
    {
      "test_case": "the test case text",
      "would_match": true or false,
      "should_match": true or false,
      "is_problematic": true if would_match != should_match
    }
  ],
  "robustness_score": number between 0-100 (100 = all test cases behave correctly)
}`;

      const analysis = await generateJSON<{
        results: Array<{
          test_case: string;
          would_match: boolean;
          should_match: boolean;
          is_problematic: boolean;
        }>;
        robustness_score: number;
      }>(analysisPrompt);

      const problematicCases = analysis.results.filter(r => r.is_problematic);
      const score = analysis.robustness_score;

      if (score < 60) {
        return {
          tool_name: "Synthetic Red Team",
          status: "FAIL",
          message: `Rule fails on ${problematicCases.length} adversarial test cases. Robustness score: ${score}/100. Rule triggers on ambiguous inputs that should not match.`,
          score,
          details: {
            adversarial_cases: problematicCases.map(r => r.test_case),
          },
        };
      } else if (score < 80) {
        return {
          tool_name: "Synthetic Red Team",
          status: "WARN",
          message: `Rule may trigger on ${problematicCases.length} edge cases. Robustness score: ${score}/100. Consider adding negative constraints.`,
          score,
          details: {
            adversarial_cases: problematicCases.map(r => r.test_case),
          },
        };
      } else {
        return {
          tool_name: "Synthetic Red Team",
          status: "PASS",
          message: `Rule is robust against adversarial attacks. Robustness score: ${score}/100.`,
          score,
        };
      }
    } catch (error) {
      console.error("Red Team Tool error:", error);
      return {
        tool_name: "Synthetic Red Team",
        status: "WARN",
        message: `Error during red team analysis: ${error instanceof Error ? error.message : "Unknown error"}`,
      };
    }
  }
}

