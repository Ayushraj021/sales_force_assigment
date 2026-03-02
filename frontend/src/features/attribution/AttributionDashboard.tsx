/**
 * Attribution Dashboard Component
 *
 * Multi-Touch Attribution analysis and visualization.
 */

import { useState, useMemo } from "react";
import { motion } from "framer-motion";

interface TouchPoint {
  channel: string;
  timestamp: string;
  campaign?: string;
}

interface Journey {
  id: string;
  touchpoints: TouchPoint[];
  conversion: boolean;
  conversionValue: number;
}

interface AttributionResult {
  channel: string;
  firstTouch: number;
  lastTouch: number;
  linear: number;
  timeDecay: number;
  positionBased: number;
  shapley: number;
  markov: number;
}

interface AttributionDashboardProps {
  journeys?: Journey[];
  attributionResults?: AttributionResult[];
  isLoading?: boolean;
  onModelChange?: (model: string) => void;
  onDateRangeChange?: (start: string, end: string) => void;
}

const mockResults: AttributionResult[] = [
  { channel: "Paid Search", firstTouch: 0.35, lastTouch: 0.28, linear: 0.25, timeDecay: 0.26, positionBased: 0.30, shapley: 0.27, markov: 0.29 },
  { channel: "Social Media", firstTouch: 0.25, lastTouch: 0.15, linear: 0.18, timeDecay: 0.16, positionBased: 0.20, shapley: 0.19, markov: 0.17 },
  { channel: "Email", firstTouch: 0.10, lastTouch: 0.22, linear: 0.20, timeDecay: 0.21, positionBased: 0.18, shapley: 0.20, markov: 0.19 },
  { channel: "Display", firstTouch: 0.18, lastTouch: 0.10, linear: 0.12, timeDecay: 0.11, positionBased: 0.14, shapley: 0.13, markov: 0.12 },
  { channel: "Organic Search", firstTouch: 0.08, lastTouch: 0.18, linear: 0.15, timeDecay: 0.17, positionBased: 0.12, shapley: 0.14, markov: 0.16 },
  { channel: "Direct", firstTouch: 0.04, lastTouch: 0.07, linear: 0.10, timeDecay: 0.09, positionBased: 0.06, shapley: 0.07, markov: 0.07 },
];

const attributionModels = [
  { id: "firstTouch", name: "First Touch", description: "100% credit to first interaction" },
  { id: "lastTouch", name: "Last Touch", description: "100% credit to last interaction" },
  { id: "linear", name: "Linear", description: "Equal credit to all touchpoints" },
  { id: "timeDecay", name: "Time Decay", description: "More credit to recent touchpoints" },
  { id: "positionBased", name: "Position Based", description: "40-20-40 split (first, middle, last)" },
  { id: "shapley", name: "Shapley Value", description: "Game theory based attribution" },
  { id: "markov", name: "Markov Chain", description: "Probabilistic attribution model" },
];

export function AttributionDashboard({
  journeys,
  attributionResults = mockResults,
  isLoading = false,
  onModelChange,
  onDateRangeChange,
}: AttributionDashboardProps) {
  const [selectedModel, setSelectedModel] = useState("shapley");
  const [comparisonModel, setComparisonModel] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({ start: "2024-01-01", end: "2024-01-31" });
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");

  const sortedResults = useMemo(() => {
    return [...attributionResults].sort((a, b) => {
      const aVal = a[selectedModel as keyof AttributionResult] as number;
      const bVal = b[selectedModel as keyof AttributionResult] as number;
      return bVal - aVal;
    });
  }, [attributionResults, selectedModel]);

  const totalConversions = 1000; // Mock total
  const totalRevenue = 125000; // Mock revenue

  const getModelValue = (result: AttributionResult, model: string): number => {
    return result[model as keyof AttributionResult] as number;
  };

  const formatPercent = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Attribution Analysis
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Understand the contribution of each marketing channel to conversions
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Attribution Model</label>
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  onModelChange?.(e.target.value);
                }}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
              >
                {attributionModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Compare With</label>
              <select
                value={comparisonModel || ""}
                onChange={(e) => setComparisonModel(e.target.value || null)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
              >
                <option value="">None</option>
                {attributionModels
                  .filter((m) => m.id !== selectedModel)
                  .map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
              </select>
            </div>
          </div>
          <div className="flex gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Start Date</label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => {
                  setDateRange((prev) => ({ ...prev, start: e.target.value }));
                  onDateRangeChange?.(e.target.value, dateRange.end);
                }}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">End Date</label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => {
                  setDateRange((prev) => ({ ...prev, end: e.target.value }));
                  onDateRangeChange?.(dateRange.start, e.target.value);
                }}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Total Conversions</div>
          <div className="text-2xl font-bold mt-1">{totalConversions.toLocaleString()}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Total Revenue</div>
          <div className="text-2xl font-bold mt-1">{formatCurrency(totalRevenue)}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Avg. Touchpoints</div>
          <div className="text-2xl font-bold mt-1">4.2</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Conversion Rate</div>
          <div className="text-2xl font-bold mt-1">3.8%</div>
        </div>
      </div>

      {/* Model Description */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-6 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-blue-700 dark:text-blue-300">
            {attributionModels.find((m) => m.id === selectedModel)?.name}:
          </span>
          <span className="text-blue-600 dark:text-blue-400">
            {attributionModels.find((m) => m.id === selectedModel)?.description}
          </span>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setViewMode("chart")}
          className={`px-4 py-2 text-sm rounded-md ${
            viewMode === "chart"
              ? "bg-primary text-white"
              : "bg-gray-200 dark:bg-gray-700"
          }`}
        >
          Chart View
        </button>
        <button
          onClick={() => setViewMode("table")}
          className={`px-4 py-2 text-sm rounded-md ${
            viewMode === "table"
              ? "bg-primary text-white"
              : "bg-gray-200 dark:bg-gray-700"
          }`}
        >
          Table View
        </button>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : viewMode === "chart" ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700"
        >
          <h3 className="text-lg font-semibold mb-4">Channel Attribution</h3>
          <div className="space-y-4">
            {sortedResults.map((result, index) => {
              const value = getModelValue(result, selectedModel);
              const compareValue = comparisonModel
                ? getModelValue(result, comparisonModel)
                : null;
              const diff = compareValue ? value - compareValue : null;

              return (
                <motion.div
                  key={result.channel}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="space-y-1"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{result.channel}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-lg font-bold">{formatPercent(value)}</span>
                      {diff !== null && (
                        <span
                          className={`text-sm ${
                            diff > 0
                              ? "text-green-600"
                              : diff < 0
                              ? "text-red-600"
                              : "text-gray-500"
                          }`}
                        >
                          {diff > 0 ? "+" : ""}
                          {formatPercent(diff)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="relative h-6 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${value * 100}%` }}
                      transition={{ duration: 0.5, delay: index * 0.05 }}
                      className="absolute h-full bg-primary rounded-full"
                    />
                    {compareValue && (
                      <div
                        className="absolute h-full border-r-2 border-gray-400"
                        style={{ left: `${compareValue * 100}%` }}
                      />
                    )}
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Conversions: {Math.round(value * totalConversions)}</span>
                    <span>Revenue: {formatCurrency(value * totalRevenue)}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Channel</th>
                  {attributionModels.map((model) => (
                    <th
                      key={model.id}
                      className={`px-4 py-3 text-right text-sm font-semibold ${
                        model.id === selectedModel
                          ? "bg-primary/10 text-primary"
                          : ""
                      }`}
                    >
                      {model.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {sortedResults.map((result) => (
                  <tr key={result.channel} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3 font-medium">{result.channel}</td>
                    {attributionModels.map((model) => {
                      const value = getModelValue(result, model.id);
                      return (
                        <td
                          key={model.id}
                          className={`px-4 py-3 text-right ${
                            model.id === selectedModel
                              ? "bg-primary/10 font-bold"
                              : ""
                          }`}
                        >
                          {formatPercent(value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Channel Synergy Analysis */}
      <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Channel Synergies</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Channels that frequently appear together in converting journeys
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="font-medium">Paid Search + Email</span>
              <span className="text-green-600 dark:text-green-400">+23% lift</span>
            </div>
            <div className="text-sm text-gray-500 mt-1">Appears in 34% of journeys</div>
          </div>
          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="font-medium">Social + Display</span>
              <span className="text-green-600 dark:text-green-400">+15% lift</span>
            </div>
            <div className="text-sm text-gray-500 mt-1">Appears in 28% of journeys</div>
          </div>
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="font-medium">Display + Organic</span>
              <span className="text-blue-600 dark:text-blue-400">+12% lift</span>
            </div>
            <div className="text-sm text-gray-500 mt-1">Appears in 22% of journeys</div>
          </div>
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="font-medium">Email + Direct</span>
              <span className="text-blue-600 dark:text-blue-400">+8% lift</span>
            </div>
            <div className="text-sm text-gray-500 mt-1">Appears in 18% of journeys</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AttributionDashboard;
