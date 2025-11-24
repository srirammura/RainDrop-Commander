import { Example, AuditResult } from "./types";

export const mockRules = [
  {
    id: "rule-1",
    description: "Fails to reach documentation",
    examples: [
      { text: "Kubernetes docs 404", label: "MATCH" as const },
      { text: "Can't reach K8s docs", label: "MATCH" as const },
      { text: "Documentation server is down", label: "MATCH" as const },
      { text: "Successfully loaded docs", label: "NO_MATCH" as const },
      { text: "User logged in", label: "NO_MATCH" as const },
    ],
  },
  {
    id: "rule-2",
    description: "API authentication failure",
    examples: [
      { text: "401 Unauthorized", label: "MATCH" as const },
      { text: "Invalid API key", label: "MATCH" as const },
      { text: "Token expired", label: "MATCH" as const },
      { text: "200 OK response", label: "NO_MATCH" as const },
      { text: "Request successful", label: "NO_MATCH" as const },
    ],
  },
  {
    id: "rule-3",
    description: "Database connection error",
    examples: [
      { text: "Failed to connect to database", label: "MATCH" as const },
      { text: "DB connection timeout", label: "MATCH" as const },
      { text: "Query executed successfully", label: "NO_MATCH" as const },
    ],
  },
];

export const mockAuditHistory: AuditResult[] = [
  {
    rule_description: "Fails to reach documentation",
    examples: mockRules[0].examples,
    reports: [
      {
        tool_name: "Synthetic Red Team",
        status: "WARN",
        message: "Rule may trigger on 2 edge cases. Robustness score: 75/100. Consider adding negative constraints.",
        score: 75,
      },
      {
        tool_name: "Variance/Overfit Detector",
        status: "WARN",
        message: "Examples show limited variance. Consider adding examples with different terms. Variance score: 45/100.",
      },
      {
        tool_name: "Semantic Boundary Mapper",
        status: "PASS",
        message: "Generated 5 boundary examples inside and 5 outside the rule. Use these to refine your rule boundaries.",
      },
    ],
    executive_summary: {
      overall_status: "APPROVED_WITH_WARNINGS",
      critical_issues_count: 0,
      warnings_count: 2,
      recommendation: "Broaden your examples to include non-Kubernetes terms AND explicitly exclude 'user error' scenarios.",
    },
    timestamp: new Date(Date.now() - 3600000).toISOString(),
  },
];

export function getMockRuleById(id: string) {
  return mockRules.find((r) => r.id === id);
}

export function getAllMockRules() {
  return mockRules;
}

