/**
 * Scenario Builder Component
 *
 * Build and compare marketing scenarios with what-if analysis.
 */

import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ChannelBudget {
  channel: string;
  currentBudget: number;
  scenarioBudget: number;
  minBudget: number;
  maxBudget: number;
}

interface Scenario {
  id: string;
  name: string;
  description?: string;
  budgets: ChannelBudget[];
  projectedRevenue: number;
  projectedROI: number;
  createdAt: string;
}

interface ScenarioResult {
  scenarioId: string;
  revenue: number;
  roi: number;
  conversions: number;
  channelContributions: Record<string, number>;
  confidenceInterval: [number, number];
}

interface ScenarioBuilderProps {
  currentBudgets?: ChannelBudget[];
  scenarios?: Scenario[];
  onCreateScenario?: (scenario: Omit<Scenario, "id" | "createdAt">) => Promise<Scenario>;
  onRunSimulation?: (scenarioId: string) => Promise<ScenarioResult>;
  onCompareScenarios?: (scenarioIds: string[]) => Promise<ScenarioResult[]>;
}

const defaultBudgets: ChannelBudget[] = [
  { channel: "Paid Search", currentBudget: 50000, scenarioBudget: 50000, minBudget: 10000, maxBudget: 100000 },
  { channel: "Social Media", currentBudget: 35000, scenarioBudget: 35000, minBudget: 5000, maxBudget: 75000 },
  { channel: "Display", currentBudget: 25000, scenarioBudget: 25000, minBudget: 5000, maxBudget: 50000 },
  { channel: "Email", currentBudget: 10000, scenarioBudget: 10000, minBudget: 2000, maxBudget: 25000 },
  { channel: "TV", currentBudget: 80000, scenarioBudget: 80000, minBudget: 0, maxBudget: 200000 },
];

export function ScenarioBuilder({
  currentBudgets = defaultBudgets,
  scenarios: initialScenarios = [],
  onCreateScenario,
  onRunSimulation,
  onCompareScenarios,
}: ScenarioBuilderProps) {
  const [budgets, setBudgets] = useState<ChannelBudget[]>(currentBudgets);
  const [scenarios, setScenarios] = useState<Scenario[]>(initialScenarios);
  const [scenarioName, setScenarioName] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [comparisonResults, setComparisonResults] = useState<ScenarioResult[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showComparison, setShowComparison] = useState(false);

  const totalCurrentBudget = useMemo(
    () => budgets.reduce((sum, b) => sum + b.currentBudget, 0),
    [budgets]
  );

  const totalScenarioBudget = useMemo(
    () => budgets.reduce((sum, b) => sum + b.scenarioBudget, 0),
    [budgets]
  );

  const budgetChange = totalScenarioBudget - totalCurrentBudget;
  const budgetChangePercent = (budgetChange / totalCurrentBudget) * 100;

  const updateBudget = useCallback((channel: string, newBudget: number) => {
    setBudgets((prev) =>
      prev.map((b) =>
        b.channel === channel
          ? { ...b, scenarioBudget: Math.max(b.minBudget, Math.min(b.maxBudget, newBudget)) }
          : b
      )
    );
  }, []);

  const resetBudgets = useCallback(() => {
    setBudgets((prev) =>
      prev.map((b) => ({ ...b, scenarioBudget: b.currentBudget }))
    );
  }, []);

  const handleCreateScenario = async () => {
    if (!scenarioName.trim()) return;

    setIsLoading(true);
    try {
      const newScenario: Omit<Scenario, "id" | "createdAt"> = {
        name: scenarioName,
        description: scenarioDescription,
        budgets: [...budgets],
        projectedRevenue: totalScenarioBudget * (1.5 + Math.random() * 0.5),
        projectedROI: 1.8 + Math.random() * 0.4,
      };

      if (onCreateScenario) {
        const created = await onCreateScenario(newScenario);
        setScenarios((prev) => [...prev, created]);
      } else {
        // Mock creation
        const created: Scenario = {
          ...newScenario,
          id: `scenario-${Date.now()}`,
          createdAt: new Date().toISOString(),
        };
        setScenarios((prev) => [...prev, created]);
      }

      setScenarioName("");
      setScenarioDescription("");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompare = async () => {
    if (selectedScenarios.length < 2) return;

    setIsLoading(true);
    try {
      if (onCompareScenarios) {
        const results = await onCompareScenarios(selectedScenarios);
        setComparisonResults(results);
      } else {
        // Mock comparison
        const results: ScenarioResult[] = selectedScenarios.map((id) => ({
          scenarioId: id,
          revenue: 150000 + Math.random() * 100000,
          roi: 1.5 + Math.random() * 1,
          conversions: 1000 + Math.floor(Math.random() * 500),
          channelContributions: {
            "Paid Search": 0.3 + Math.random() * 0.1,
            "Social Media": 0.2 + Math.random() * 0.1,
            Display: 0.15 + Math.random() * 0.05,
            Email: 0.1 + Math.random() * 0.05,
            TV: 0.25 + Math.random() * 0.1,
          },
          confidenceInterval: [120000, 180000],
        }));
        setComparisonResults(results);
      }
      setShowComparison(true);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleScenarioSelection = (id: string) => {
    setSelectedScenarios((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Scenario Builder
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Create and compare budget allocation scenarios
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Budget Editor */}
        <div className="col-span-2 space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Budget Allocation</h3>
              <button
                onClick={resetBudgets}
                className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Reset to Current
              </button>
            </div>

            <div className="space-y-4">
              {budgets.map((budget) => {
                const change = budget.scenarioBudget - budget.currentBudget;
                const changePercent = (change / budget.currentBudget) * 100;

                return (
                  <div key={budget.channel} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{budget.channel}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-500">
                          Current: {formatCurrency(budget.currentBudget)}
                        </span>
                        <span className="font-semibold">
                          {formatCurrency(budget.scenarioBudget)}
                        </span>
                        {change !== 0 && (
                          <span
                            className={`text-sm ${
                              change > 0 ? "text-green-600" : "text-red-600"
                            }`}
                          >
                            {change > 0 ? "+" : ""}
                            {changePercent.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                    <input
                      type="range"
                      min={budget.minBudget}
                      max={budget.maxBudget}
                      value={budget.scenarioBudget}
                      onChange={(e) =>
                        updateBudget(budget.channel, parseInt(e.target.value))
                      }
                      className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{formatCurrency(budget.minBudget)}</span>
                      <span>{formatCurrency(budget.maxBudget)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Total */}
            <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="font-semibold">Total Budget</span>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500">
                    Current: {formatCurrency(totalCurrentBudget)}
                  </span>
                  <span className="text-xl font-bold">
                    {formatCurrency(totalScenarioBudget)}
                  </span>
                  {budgetChange !== 0 && (
                    <span
                      className={`text-sm font-medium ${
                        budgetChange > 0 ? "text-green-600" : "text-red-600"
                      }`}
                    >
                      {budgetChange > 0 ? "+" : ""}
                      {budgetChangePercent.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Save Scenario */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Save Scenario</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Scenario Name</label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  placeholder="e.g., Q2 Growth Plan"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description (optional)</label>
                <textarea
                  value={scenarioDescription}
                  onChange={(e) => setScenarioDescription(e.target.value)}
                  placeholder="Describe this scenario..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                />
              </div>
              <button
                onClick={handleCreateScenario}
                disabled={!scenarioName.trim() || isLoading}
                className="w-full px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? "Saving..." : "Save Scenario"}
              </button>
            </div>
          </div>
        </div>

        {/* Saved Scenarios */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Saved Scenarios</h3>

            {scenarios.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">
                No scenarios saved yet
              </p>
            ) : (
              <div className="space-y-3">
                {scenarios.map((scenario) => (
                  <motion.div
                    key={scenario.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedScenarios.includes(scenario.id)
                        ? "bg-primary/10 border border-primary"
                        : "bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                    }`}
                    onClick={() => toggleScenarioSelection(scenario.id)}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedScenarios.includes(scenario.id)}
                        onChange={() => toggleScenarioSelection(scenario.id)}
                        className="w-4 h-4 text-primary"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="font-medium">{scenario.name}</span>
                    </div>
                    <div className="mt-2 text-sm text-gray-500">
                      <div>Total: {formatCurrency(scenario.budgets.reduce((s, b) => s + b.scenarioBudget, 0))}</div>
                      <div>Projected ROI: {scenario.projectedROI.toFixed(2)}x</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {scenarios.length >= 2 && (
              <button
                onClick={handleCompare}
                disabled={selectedScenarios.length < 2 || isLoading}
                className="w-full mt-4 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? "Comparing..." : `Compare (${selectedScenarios.length} selected)`}
              </button>
            )}
          </div>

          {/* Quick Projections */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Quick Projections</h3>
            <div className="space-y-4">
              <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="text-sm text-gray-500">Projected Revenue</div>
                <div className="text-xl font-bold text-green-600">
                  {formatCurrency(totalScenarioBudget * 1.65)}
                </div>
              </div>
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="text-sm text-gray-500">Projected ROI</div>
                <div className="text-xl font-bold text-blue-600">1.85x</div>
              </div>
              <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <div className="text-sm text-gray-500">Expected Conversions</div>
                <div className="text-xl font-bold text-purple-600">
                  {Math.round(totalScenarioBudget / 150).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Results Modal */}
      <AnimatePresence>
        {showComparison && comparisonResults && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowComparison(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold">Scenario Comparison</h2>
                <button
                  onClick={() => setShowComparison(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  Close
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Metric</th>
                      {comparisonResults.map((result) => {
                        const scenario = scenarios.find((s) => s.id === result.scenarioId);
                        return (
                          <th key={result.scenarioId} className="px-4 py-3 text-right text-sm font-semibold">
                            {scenario?.name || result.scenarioId}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    <tr>
                      <td className="px-4 py-3 font-medium">Revenue</td>
                      {comparisonResults.map((result) => (
                        <td key={result.scenarioId} className="px-4 py-3 text-right">
                          {formatCurrency(result.revenue)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium">ROI</td>
                      {comparisonResults.map((result) => (
                        <td key={result.scenarioId} className="px-4 py-3 text-right">
                          {result.roi.toFixed(2)}x
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium">Conversions</td>
                      {comparisonResults.map((result) => (
                        <td key={result.scenarioId} className="px-4 py-3 text-right">
                          {result.conversions.toLocaleString()}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-medium">95% CI</td>
                      {comparisonResults.map((result) => (
                        <td key={result.scenarioId} className="px-4 py-3 text-right text-sm">
                          [{formatCurrency(result.confidenceInterval[0])} - {formatCurrency(result.confidenceInterval[1])}]
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <p className="text-green-700 dark:text-green-300">
                  <span className="font-semibold">Recommendation:</span>{" "}
                  Based on projected ROI, scenario "{scenarios.find(s => s.id === comparisonResults.reduce((best, r) =>
                    r.roi > (comparisonResults.find(c => c.scenarioId === best)?.roi || 0) ? r.scenarioId : best,
                    comparisonResults[0]?.scenarioId
                  ))?.name}" offers the best return on investment.
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ScenarioBuilder;
