"use client";

interface InteractionBlockProps {
  userMessage: string;
  assistantMessage: string;
  highlightText?: string;
}

export default function InteractionBlock({
  userMessage,
  assistantMessage,
  highlightText,
}: InteractionBlockProps) {
  return (
    <div className="space-y-4">
      <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
        <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
          USER
        </div>
        <p className="text-gray-900 dark:text-gray-100">{userMessage}</p>
      </div>

      {highlightText && (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-300 font-medium">
            {highlightText}
          </p>
        </div>
      )}

      <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-4">
        <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-2">
          ASSISTANT
        </div>
        <p className="text-blue-900 dark:text-blue-200">{assistantMessage}</p>
      </div>

      <div className="flex gap-2">
        <button className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-semibold">
          HELPFUL
        </button>
        <button className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-semibold">
          NOT HELPFUL
        </button>
      </div>
    </div>
  );
}

