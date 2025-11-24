"use client";

import { useState } from "react";
import { Example } from "@/lib/types";
import { getAllMockRules } from "@/lib/mock-data";

interface RuleInputProps {
  onSubmit: (rule: string, examples: Example[]) => void;
  isLoading?: boolean;
}

export default function RuleInput({ onSubmit, isLoading }: RuleInputProps) {
  const [ruleDescription, setRuleDescription] = useState("");
  const [examples, setExamples] = useState<Example[]>([
    { text: "", label: "MATCH" },
  ]);

  const addExample = () => {
    setExamples([...examples, { text: "", label: "MATCH" }]);
  };

  const removeExample = (index: number) => {
    setExamples(examples.filter((_, i) => i !== index));
  };

  const updateExample = (index: number, field: "text" | "label", value: string) => {
    const updated = [...examples];
    updated[index] = { ...updated[index], [field]: value };
    setExamples(updated);
  };

  const loadMockRule = (ruleId: string) => {
    const mockRules = getAllMockRules();
    const rule = mockRules.find((r) => r.id === ruleId);
    if (rule) {
      setRuleDescription(rule.description);
      setExamples(rule.examples);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const validExamples = examples.filter((ex) => ex.text.trim() !== "");
    if (ruleDescription.trim() && validExamples.length > 0) {
      onSubmit(ruleDescription, validExamples);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
      <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
        Rule Input
      </h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Rule Description
        </label>
        <textarea
          value={ruleDescription}
          onChange={(e) => setRuleDescription(e.target.value)}
          placeholder="e.g., Fails to reach documentation"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
        />
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Examples
          </label>
          <button
            type="button"
            onClick={addExample}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            + Add Example
          </button>
        </div>
        <div className="space-y-2">
          {examples.map((example, index) => (
            <div key={index} className="flex gap-2 items-center">
              <input
                type="text"
                value={example.text}
                onChange={(e) => updateExample(index, "text", e.target.value)}
                placeholder="Example text..."
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={example.label}
                onChange={(e) =>
                  updateExample(index, "label", e.target.value as "MATCH" | "NO_MATCH")
                }
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="MATCH">MATCH</option>
                <option value="NO_MATCH">NO_MATCH</option>
              </select>
              {examples.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeExample(index)}
                  className="px-2 py-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 rounded"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Load Mock Rule (Demo)
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => loadMockRule("rule-1")}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            Rule 1: Docs 404
          </button>
          <button
            type="button"
            onClick={() => loadMockRule("rule-2")}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            Rule 2: Auth Failure
          </button>
          <button
            type="button"
            onClick={() => loadMockRule("rule-3")}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            Rule 3: DB Error
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isLoading || !ruleDescription.trim() || examples.filter((e) => e.text.trim()).length === 0}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-semibold"
      >
        {isLoading ? "Auditing..." : "🚀 Run Commander Audit"}
      </button>
    </div>
  );
}

