export interface Example {
  text: string;
  label: "MATCH" | "NO_MATCH";
}

export interface ToolReport {
  tool_name: string;
  status: "PASS" | "WARN" | "FAIL";
  message: string;
  score?: number; // 0-100 for tools that provide scores
  details?: {
    adversarial_cases?: string[];
    boundary_examples_inside?: string[];
    boundary_examples_outside?: string[];
    detected_patterns?: string[];
  };
}

export interface AuditResult {
  rule_description: string;
  examples: Example[];
  reports: ToolReport[];
  executive_summary: {
    overall_status: "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED";
    critical_issues_count: number;
    warnings_count: number;
    recommendation: string;
  };
  timestamp: string;
}

export interface AuditRequest {
  rule_description: string;
  examples: Example[];
}

