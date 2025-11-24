"use client";

import { useState } from "react";
import { AuditResult, Example } from "@/lib/types";
import RuleInput from "./RuleInput";
import AuditResults from "./AuditResults";
import InteractionBlock from "./InteractionBlock";
import DataVisualization from "./DataVisualization";
import FeatureHighlights from "./FeatureHighlights";
import PricingSection from "./PricingSection";

export default function CommanderDashboard() {
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAudit = async (rule: string, examples: Example[]) => {
    setIsLoading(true);
    setError(null);
    setAuditResult(null);

    try {
      const response = await fetch("/api/commander/audit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          rule_description: rule,
          examples,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to audit rule");
      }

      const result: AuditResult = await response.json();
      setAuditResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Top Section - Dark Grid Background */}
      <div className="bg-gray-900 dark:bg-black relative overflow-hidden">
        {/* Grid Pattern */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
            `,
            backgroundSize: "20px 20px",
          }}
        ></div>

        <div className="relative z-10 max-w-6xl mx-auto px-4 py-12">
          <h1 className="text-3xl font-bold text-white mb-8">
            Training Data Curation
          </h1>

          <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-300 font-medium">
              The assistant fails to search the internet to retrieve documentation.
            </p>
          </div>

          <InteractionBlock
            userMessage="What's the correct kubectl command to stream logs from a Kubernetes pod, and can I use a wildcard in place of pod?"
            assistantMessage="Sorry, I was unable to search for Kubernetes reference."
            highlightText="The assistant fails to search the internet to retrieve documentation."
          />
        </div>
      </div>

      {/* Main Content - White Background */}
      <div className="bg-white dark:bg-gray-900">
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            {/* Left: Data Visualization */}
            <div>
              <DataVisualization />
            </div>

            {/* Right: Rule Input */}
            <div>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  CAN YOU DESCRIBE IT? THEN TRACK IT.
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  Enter your rule and examples to run a comprehensive audit.
                </p>
              </div>
              <RuleInput onSubmit={handleAudit} isLoading={isLoading} />
            </div>
          </div>

          {/* Audit Results */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-800 dark:text-red-300">{error}</p>
            </div>
          )}

          {auditResult && (
            <div className="mb-12">
              <AuditResults auditResult={auditResult} />
            </div>
          )}

          {/* PII Guard Section */}
          <div className="mb-12 bg-gray-50 dark:bg-gray-800 rounded-lg p-8 border border-gray-200 dark:border-gray-700">
            <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">
              SECURE YOUR DATA WITH PII GUARD
            </h2>
            <div className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded p-4 mb-4 font-mono text-sm">
              <p className="text-gray-700 dark:text-gray-300">
                User: <span className="text-red-600 dark:text-red-400">XXXXX</span>
                <br />
                Email: <span className="text-red-600 dark:text-red-400">XXXXX@XXXXX.com</span>
                <br />
                Phone: <span className="text-red-600 dark:text-red-400">XXX-XXX-XXXX</span>
              </p>
            </div>
            <button className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold">
              LEARN MORE
            </button>
          </div>

          {/* Feature Highlights */}
          <FeatureHighlights />

          {/* Pricing */}
          <PricingSection />

          {/* Integration CTA */}
          <div className="text-center py-12">
            <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">
              IT'S REALLY EASY TO INTEGRATE
            </h2>
            <button className="px-8 py-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold text-lg">
              GET STARTED
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

