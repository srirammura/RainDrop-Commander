import { ToolReport, Example } from "../types";
import { generateJSON } from "../gemini-client";

interface BoundaryExamples {
  examples_inside: Array<{
    text: string;
    reasoning: string;
  }>;
  examples_outside: Array<{
    text: string;
    reasoning: string;
  }>;
}

export class SemanticMapperTool {
  async run(rule: string, examples: Example[]): Promise<ToolReport> {
    try {
      const prompt = `You are a semantic boundary mapper. Generate examples that help clarify the rule's boundaries.

Rule Description: "${rule}"

Positive Examples (should match):
${examples.filter(e => e.label === "MATCH").map(e => `- "${e.text}"`).join("\n")}

Negative Examples (should not match):
${examples.filter(e => e.label === "NO_MATCH").map(e => `- "${e.text}"`).join("\n") || "None provided"}

Generate:
1. 5 examples that are "barely inside" the rule boundary (should match, but are edge cases)
2. 5 examples that are "barely outside" the rule boundary (should not match, but are close)

Return a JSON object:
{
  "examples_inside": [
    {
      "text": "example text",
      "reasoning": "why this is barely inside"
    }
  ],
  "examples_outside": [
    {
      "text": "example text",
      "reasoning": "why this is barely outside"
    }
  ]
}`;

      const boundaryExamples = await generateJSON<BoundaryExamples>(prompt);

      return {
        tool_name: "Semantic Boundary Mapper",
        status: "PASS",
        message: `Generated ${boundaryExamples.examples_inside.length} boundary examples inside and ${boundaryExamples.examples_outside.length} outside the rule. Use these to refine your rule boundaries.`,
        details: {
          boundary_examples_inside: boundaryExamples.examples_inside.map(e => e.text),
          boundary_examples_outside: boundaryExamples.examples_outside.map(e => e.text),
        },
      };
    } catch (error) {
      console.error("Semantic Mapper error:", error);
      return {
        tool_name: "Semantic Boundary Mapper",
        status: "WARN",
        message: `Error during semantic mapping: ${error instanceof Error ? error.message : "Unknown error"}`,
      };
    }
  }
}

