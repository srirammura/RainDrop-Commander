"use client";

import { ToolReport } from "@/lib/types";

interface ToolReportCardProps {
  report: ToolReport;
}

export default function ToolReportCard({ report }: ToolReportCardProps) {
  const getStatusIcon = () => {
    switch (report.status) {
      case "PASS":
        return "✅";
      case "WARN":
        return "⚠️";
      case "FAIL":
        return "🛑";
      default:
        return "❓";
    }
  };

  const getStatusColor = () => {
    switch (report.status) {
      case "PASS":
        return "border-green-500 bg-green-50 dark:bg-green-950/20";
      case "WARN":
        return "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20";
      case "FAIL":
        return "border-red-500 bg-red-50 dark:bg-red-950/20";
      default:
        return "border-gray-500 bg-gray-50 dark:bg-gray-950/20";
    }
  };

  return (
    <div
      className={`border-l-4 p-4 rounded-r-lg ${getStatusColor()} dark:text-gray-100`}
    >
      <div className="flex items-start gap-2">
        <span className="text-xl">{getStatusIcon()}</span>
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-1">{report.tool_name}</h3>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {report.message}
          </p>
          {report.score !== undefined && (
            <div className="mt-2">
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                Score: {report.score}/100
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    report.score >= 80
                      ? "bg-green-500"
                      : report.score >= 60
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  }`}
                  style={{ width: `${report.score}%` }}
                ></div>
              </div>
            </div>
          )}
          {report.details && (
            <div className="mt-3 space-y-2">
              {report.details.adversarial_cases &&
                report.details.adversarial_cases.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Problematic Cases:
                    </p>
                    <ul className="text-xs text-gray-700 dark:text-gray-300 list-disc list-inside">
                      {report.details.adversarial_cases.map((case_, i) => (
                        <li key={i}>"{case_}"</li>
                      ))}
                    </ul>
                  </div>
                )}
              {report.details.boundary_examples_inside &&
                report.details.boundary_examples_inside.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Boundary Examples (Inside):
                    </p>
                    <ul className="text-xs text-gray-700 dark:text-gray-300 list-disc list-inside">
                      {report.details.boundary_examples_inside.map((ex, i) => (
                        <li key={i}>"{ex}"</li>
                      ))}
                    </ul>
                  </div>
                )}
              {report.details.boundary_examples_outside &&
                report.details.boundary_examples_outside.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Boundary Examples (Outside):
                    </p>
                    <ul className="text-xs text-gray-700 dark:text-gray-300 list-disc list-inside">
                      {report.details.boundary_examples_outside.map((ex, i) => (
                        <li key={i}>"{ex}"</li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

