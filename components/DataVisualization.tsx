"use client";

export default function DataVisualization() {
  // Mock data for visualization
  const mockData = {
    totalEvents: 1247,
    uniqueUsers: 342,
    timeline: [
      { date: "Mon", events: 120 },
      { date: "Tue", events: 145 },
      { date: "Wed", events: 132 },
      { date: "Thu", events: 158 },
      { date: "Fri", events: 142 },
      { date: "Sat", events: 98 },
      { date: "Sun", events: 112 },
    ],
  };

  const maxEvents = Math.max(...mockData.timeline.map((d) => d.events));

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Analytics Dashboard
        </h3>
        <div className="flex gap-6">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Total Events</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {mockData.totalEvents.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Unique Users</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {mockData.uniqueUsers.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="flex items-end gap-2 h-32">
          {mockData.timeline.map((day, i) => (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-blue-500 dark:bg-blue-600 rounded-t hover:bg-blue-600 dark:hover:bg-blue-500 transition-colors"
                style={{
                  height: `${(day.events / maxEvents) * 100}%`,
                }}
                title={`${day.date}: ${day.events} events`}
              ></div>
              <span className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                {day.date}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
          Filter by
        </button>
        <button className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
          Add label
        </button>
        <button className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
          Add to dataset
        </button>
      </div>
    </div>
  );
}

