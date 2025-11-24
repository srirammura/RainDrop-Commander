import { AuditResult, ToolReport, Example } from "./types";
import { RedTeamTool } from "./tools/red-team-tool";
import { OverfitDetectorTool } from "./tools/overfit-detector";
import { SemanticMapperTool } from "./tools/semantic-mapper";
import { generateText } from "./gemini-client";

export class CommanderAgent {
  private rule: string;
  private examples: Example[];
  private tools: [RedTeamTool, OverfitDetectorTool, SemanticMapperTool];

  constructor(rule_description: string, examples: Example[]) {
    this.rule = rule_description;
    this.examples = examples;
    this.tools = [
      new RedTeamTool(),
      new OverfitDetectorTool(),
      new SemanticMapperTool(),
    ];
  }

  async auditRule(): Promise<AuditResult> {
    console.log(`👮 COMMANDER: Auditing rule '${this.rule}'...`);

    const reports: ToolReport[] = [];

    // Run all tools sequentially
    for (const tool of this.tools) {
      const toolName = tool.constructor.name;
      console.log(`   ↳ Running ${toolName}...`);
      
      try {
        const report = await tool.run(this.rule, this.examples);
        reports.push(report);
      } catch (error) {
        console.error(`Error running ${toolName}:`, error);
        reports.push({
          tool_name: toolName,
          status: "WARN",
          message: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        });
      }
    }

    // Synthesize executive summary
    const executiveSummary = await this.generateExecutiveSummary(reports);

    return {
      rule_description: this.rule,
      examples: this.examples,
      reports,
      executive_summary: executiveSummary,
      timestamp: new Date().toISOString(),
    };
  }

  private async generateExecutiveSummary(
    reports: ToolReport[]
  ): Promise<AuditResult["executive_summary"]> {
    const criticalIssues = reports.filter((r) => r.status === "FAIL");
    const warnings = reports.filter((r) => r.status === "WARN");
    const passes = reports.filter((r) => r.status === "PASS");

    let overallStatus: "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED";
    if (criticalIssues.length > 0) {
      overallStatus = "REJECTED";
    } else if (warnings.length > 0) {
      overallStatus = "APPROVED_WITH_WARNINGS";
    } else {
      overallStatus = "APPROVED";
    }

    // Generate recommendation using LLM
    const recommendationPrompt = `Based on these audit reports, provide a concise recommendation for improving the rule.

Rule: "${this.rule}"

Reports:
${reports.map(r => `[${r.status}] ${r.tool_name}: ${r.message}`).join("\n")}

Provide a single, actionable recommendation (2-3 sentences max) on how to improve the rule based on these findings.`;

    let recommendation = "No issues detected. Rule is ready for deployment.";
    
    if (criticalIssues.length > 0 || warnings.length > 0) {
      try {
        recommendation = await generateText(recommendationPrompt, {
          temperature: 0.7,
          maxTokens: 200,
        });
      } catch (error) {
        console.error("Error generating recommendation:", error);
        recommendation = "Review the warnings and failures above to improve the rule.";
      }
    }

    return {
      overall_status: overallStatus,
      critical_issues_count: criticalIssues.length,
      warnings_count: warnings.length,
      recommendation,
    };
  }
}

