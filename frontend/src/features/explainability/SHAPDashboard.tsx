/**
 * SHAP Explainability Dashboard
 *
 * Visualize model explanations using SHAP values.
 */

import { useState, useMemo } from "react";
import { motion } from "framer-motion";

interface SHAPValue {
  feature: string;
  value: number;
  importance: number;
  direction: "positive" | "negative";
}

interface FeatureImportance {
  feature: string;
  importance: number;
  meanAbsShap: number;
}

interface SHAPDashboardProps {
  modelId?: string;
  shapValues?: SHAPValue[];
  featureImportance?: FeatureImportance[];
  isLoading?: boolean;
  onFeatureSelect?: (feature: string) => void;
  onExplainInstance?: (instanceId: string) => Promise<SHAPValue[]>;
}

const mockFeatureImportance: FeatureImportance[] = [
  { feature: "tv_spend", importance: 0.32, meanAbsShap: 0.28 },
  { feature: "digital_spend", importance: 0.24, meanAbsShap: 0.21 },
  { feature: "seasonality", importance: 0.18, meanAbsShap: 0.16 },
  { feature: "price", importance: 0.12, meanAbsShap: 0.11 },
  { feature: "competitor_activity", importance: 0.08, meanAbsShap: 0.09 },
  { feature: "promotion_flag", importance: 0.06, meanAbsShap: 0.05 },
];

const mockShapValues: SHAPValue[] = [
  { feature: "tv_spend", value: 0.45, importance: 0.32, direction: "positive" },
  { feature: "digital_spend", value: 0.28, importance: 0.24, direction: "positive" },
  { feature: "seasonality", value: -0.15, importance: 0.18, direction: "negative" },
  { feature: "price", value: -0.22, importance: 0.12, direction: "negative" },
  { feature: "competitor_activity", value: 0.08, importance: 0.08, direction: "positive" },
  { feature: "promotion_flag", value: 0.12, importance: 0.06, direction: "positive" },
];

export function SHAPDashboard({
  modelId = "mmm-model-1",
  shapValues = mockShapValues,
  featureImportance = mockFeatureImportance,
  isLoading = false,
  onFeatureSelect,
  onExplainInstance,
}: SHAPDashboardProps) {
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"summary" | "waterfall" | "dependence">("summary");
  const [instanceId, setInstanceId] = useState("");

  const sortedImportance = useMemo(() => {
    return [...featureImportance].sort((a, b) => b.importance - a.importance);
  }, [featureImportance]);

  const sortedShap = useMemo(() => {
    return [...shapValues].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  }, [shapValues]);

  const baseValue = 0.5;
  const prediction = baseValue + sortedShap.reduce((sum, v) => sum + v.value, 0);

  const handleFeatureClick = (feature: string) => {
    setSelectedFeature(feature);
    onFeatureSelect?.(feature);
  };

  const handleExplainInstance = async () => {
    if (instanceId && onExplainInstance) {
      await onExplainInstance(instanceId);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Model Explainability
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Understand how your model makes predictions using SHAP values
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode("summary")}
              className={`px-4 py-2 text-sm rounded-md ${
                viewMode === "summary"
                  ? "bg-primary text-white"
                  : "bg-gray-200 dark:bg-gray-700"
              }`}
            >
              Summary Plot
            </button>
            <button
              onClick={() => setViewMode("waterfall")}
              className={`px-4 py-2 text-sm rounded-md ${
                viewMode === "waterfall"
                  ? "bg-primary text-white"
                  : "bg-gray-200 dark:bg-gray-700"
              }`}
            >
              Waterfall
            </button>
            <button
              onClick={() => setViewMode("dependence")}
              className={`px-4 py-2 text-sm rounded-md ${
                viewMode === "dependence"
                  ? "bg-primary text-white"
                  : "bg-gray-200 dark:bg-gray-700"
              }`}
            >
              Dependence
            </button>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={instanceId}
              onChange={(e) => setInstanceId(e.target.value)}
              placeholder="Enter instance ID..."
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            />
            <button
              onClick={handleExplainInstance}
              disabled={!instanceId}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              Explain
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Model ID</div>
          <div className="text-lg font-bold mt-1">{modelId}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Base Value</div>
          <div className="text-lg font-bold mt-1">{baseValue.toFixed(3)}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Features</div>
          <div className="text-lg font-bold mt-1">{featureImportance.length}</div>
        </div>
      </div>

      {isLoading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : (
        <>
          {/* Summary View */}
          {viewMode === "summary" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-lg font-semibold mb-4">Feature Importance</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Mean absolute SHAP value for each feature across all predictions
              </p>
              <div className="space-y-4">
                {sortedImportance.map((item, index) => (
                  <motion.div
                    key={item.feature}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`cursor-pointer rounded-lg p-3 transition-colors ${
                      selectedFeature === item.feature
                        ? "bg-primary/10 border border-primary"
                        : "hover:bg-gray-50 dark:hover:bg-gray-700"
                    }`}
                    onClick={() => handleFeatureClick(item.feature)}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium">{item.feature}</span>
                      <span className="text-sm text-gray-500">
                        {(item.importance * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${item.importance * 100}%` }}
                        transition={{ duration: 0.5, delay: index * 0.05 }}
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Waterfall View */}
          {viewMode === "waterfall" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-lg font-semibold mb-4">Waterfall Plot</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                How each feature contributes to the prediction for this instance
              </p>

              {/* Base Value */}
              <div className="flex items-center gap-4 mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
                <span className="w-40 text-sm font-medium">Base Value</span>
                <div className="flex-1 flex items-center justify-center">
                  <div className="w-4 h-4 rounded-full bg-gray-400" />
                </div>
                <span className="w-20 text-right font-mono">{baseValue.toFixed(3)}</span>
              </div>

              {/* SHAP Values */}
              <div className="space-y-2">
                {sortedShap.map((item, index) => {
                  const isPositive = item.value >= 0;
                  const barWidth = Math.abs(item.value) * 100;

                  return (
                    <motion.div
                      key={item.feature}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center gap-4"
                    >
                      <span className="w-40 text-sm font-medium truncate">
                        {item.feature}
                      </span>
                      <div className="flex-1 flex items-center">
                        <div className="w-1/2 flex justify-end">
                          {!isPositive && (
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${barWidth}%` }}
                              className="h-6 bg-red-500 rounded-l"
                            />
                          )}
                        </div>
                        <div className="w-px h-8 bg-gray-300 dark:bg-gray-600" />
                        <div className="w-1/2">
                          {isPositive && (
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${barWidth}%` }}
                              className="h-6 bg-green-500 rounded-r"
                            />
                          )}
                        </div>
                      </div>
                      <span
                        className={`w-20 text-right font-mono ${
                          isPositive ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {isPositive ? "+" : ""}
                        {item.value.toFixed(3)}
                      </span>
                    </motion.div>
                  );
                })}
              </div>

              {/* Prediction */}
              <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <span className="w-40 text-sm font-bold">Prediction</span>
                <div className="flex-1 flex items-center justify-center">
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                    <span className="text-white text-xs">=</span>
                  </div>
                </div>
                <span className="w-20 text-right font-mono font-bold">
                  {prediction.toFixed(3)}
                </span>
              </div>
            </motion.div>
          )}

          {/* Dependence View */}
          {viewMode === "dependence" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-lg font-semibold mb-4">Feature Dependence</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                How the feature value affects its SHAP contribution
              </p>

              {/* Feature Selector */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Select Feature</label>
                <select
                  value={selectedFeature || ""}
                  onChange={(e) => setSelectedFeature(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                >
                  <option value="">Choose a feature...</option>
                  {sortedImportance.map((item) => (
                    <option key={item.feature} value={item.feature}>
                      {item.feature}
                    </option>
                  ))}
                </select>
              </div>

              {selectedFeature ? (
                <div className="relative h-64 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  {/* Mock scatter plot visualization */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="grid grid-cols-10 gap-1 p-4">
                      {Array.from({ length: 50 }).map((_, i) => {
                        const x = (i % 10) * 10;
                        const y = Math.sin(i / 5) * 40 + 50 + Math.random() * 20;
                        const color = y > 50 ? "bg-green-500" : "bg-red-500";
                        return (
                          <div
                            key={i}
                            className={`w-2 h-2 rounded-full ${color}`}
                            style={{
                              transform: `translateY(${100 - y}px)`,
                              opacity: 0.7,
                            }}
                          />
                        );
                      })}
                    </div>
                  </div>

                  {/* Axes labels */}
                  <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-sm text-gray-500">
                    {selectedFeature} Value
                  </div>
                  <div className="absolute left-0 top-1/2 transform -rotate-90 -translate-x-1/2 -translate-y-1/2 text-sm text-gray-500">
                    SHAP Value
                  </div>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  Select a feature to view its dependence plot
                </div>
              )}
            </motion.div>
          )}
        </>
      )}

      {/* Interpretation Guide */}
      <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
        <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-2">
          How to Interpret SHAP Values
        </h4>
        <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
          <li>
            <span className="font-medium">Positive SHAP values</span> push the prediction higher
          </li>
          <li>
            <span className="font-medium">Negative SHAP values</span> push the prediction lower
          </li>
          <li>
            <span className="font-medium">Feature importance</span> is the mean absolute SHAP value
          </li>
          <li>
            SHAP values are additive: base value + sum(SHAP values) = prediction
          </li>
        </ul>
      </div>
    </div>
  );
}

export default SHAPDashboard;
