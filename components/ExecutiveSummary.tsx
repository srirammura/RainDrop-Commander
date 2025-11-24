"use client";

import { AuditResult } from "@/lib/types";

interface ExecutiveSummaryProps {
  auditResult: AuditResult;
}

export default function ExecutiveSummary({
  auditResult,
}: ExecutiveSummaryProps) {
  const { executive_summary } = auditResult;

  const getStatusBadge = () => {
    switch (executive_summary.overall_status) {
      case "APPROVED":
        return (
          <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full text-sm font-semibold">
            ✅ APPROVED
          </span>
        );
      case "APPROVED_WITH_WARNINGS":
        return (
          <span className="px-3 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded-full text-sm font-semibold">
            ⚠️ APPROVED WITH WARNINGS
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 rounded-full text-sm font-semibold">
            🛑 REJECTED
          </span>
        );
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
      <div className="mb-4">
        <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-white">
          📋 COMMANDER EXECUTIVE SUMMARY
        </h2>
        <div className="flex items-center gap-4 mt-3">
          {getStatusBadge()}
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {executive_summary.critical_issues_count} Errors,{" "}
            {executive_summary.warnings_count} Warnings
          </span>
        </div>
      </div>

      {executive_summary.overall_status !== "APPROVED" && (
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">
            💡 COMMANDER RECOMMENDATION:
          </p>
          <p className="text-sm text-blue-800 dark:text-blue-200">
            {executive_summary.recommendation}
          </p>
        </div>
      )}

      {executive_summary.overall_status === "APPROVED" && (
        <div className="mt-4 p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-sm text-green-800 dark:text-green-200">
            ✅ Rule is safe to deploy. All checks passed.
          </p>
        </div>
      )}
    </div>
  );
}

