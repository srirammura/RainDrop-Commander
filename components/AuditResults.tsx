"use client";

import { AuditResult } from "@/lib/types";
import ToolReportCard from "./ToolReportCard";
import ExecutiveSummary from "./ExecutiveSummary";

interface AuditResultsProps {
  auditResult: AuditResult | null;
}

export default function AuditResults({ auditResult }: AuditResultsProps) {
  if (!auditResult) {
    return null;
  }

  return (
    <div className="space-y-6">
      <ExecutiveSummary auditResult={auditResult} />

      <div>
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          Tool Reports
        </h2>
        <div className="space-y-4">
          {auditResult.reports.map((report, index) => (
            <ToolReportCard key={index} report={report} />
          ))}
        </div>
      </div>
    </div>
  );
}

