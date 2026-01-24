/**
 * GeoLift Experiment Component
 *
 * UI for designing and analyzing geographic lift tests.
 */

import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Region {
  id: string;
  name: string;
  population: number;
  baselineMetric: number;
  isTest: boolean;
  isControl: boolean;
}

interface ExperimentConfig {
  name: string;
  description: string;
  startDate: string;
  endDate: string;
  testRegions: string[];
  controlRegions: string[];
  primaryMetric: string;
  secondaryMetrics: string[];
  confidenceLevel: number;
  minimumDetectableEffect: number;
}

interface PowerAnalysis {
  sampleSize: number;
  power: number;
  mde: number;
  duration: number;
  expectedLift: number;
}

interface ExperimentResult {
  lift: number;
  liftCI: [number, number];
  pValue: number;
  isSignificant: boolean;
  attPerRegion: Record<string, number>;
}

interface GeoLiftExperimentProps {
  regions?: Region[];
  onSave?: (config: ExperimentConfig) => Promise<void>;
  onRunPowerAnalysis?: (config: ExperimentConfig) => Promise<PowerAnalysis>;
  onAnalyzeResults?: (experimentId: string) => Promise<ExperimentResult>;
}

const defaultRegions: Region[] = [
  { id: "ny", name: "New York", population: 8336817, baselineMetric: 125000, isTest: false, isControl: false },
  { id: "la", name: "Los Angeles", population: 3979576, baselineMetric: 98000, isTest: false, isControl: false },
  { id: "chi", name: "Chicago", population: 2693976, baselineMetric: 67000, isTest: false, isControl: false },
  { id: "hou", name: "Houston", population: 2320268, baselineMetric: 58000, isTest: false, isControl: false },
  { id: "phx", name: "Phoenix", population: 1680992, baselineMetric: 42000, isTest: false, isControl: false },
  { id: "phi", name: "Philadelphia", population: 1584064, baselineMetric: 39000, isTest: false, isControl: false },
  { id: "sa", name: "San Antonio", population: 1547253, baselineMetric: 38000, isTest: false, isControl: false },
  { id: "sd", name: "San Diego", population: 1423851, baselineMetric: 36000, isTest: false, isControl: false },
];

export function GeoLiftExperiment({
  regions: initialRegions = defaultRegions,
  onSave,
  onRunPowerAnalysis,
  onAnalyzeResults,
}: GeoLiftExperimentProps) {
  const [step, setStep] = useState<"design" | "power" | "monitor" | "analyze">("design");
  const [regions, setRegions] = useState<Region[]>(initialRegions);
  const [config, setConfig] = useState<ExperimentConfig>({
    name: "",
    description: "",
    startDate: "",
    endDate: "",
    testRegions: [],
    controlRegions: [],
    primaryMetric: "conversions",
    secondaryMetrics: [],
    confidenceLevel: 0.95,
    minimumDetectableEffect: 0.05,
  });
  const [powerAnalysis, setPowerAnalysis] = useState<PowerAnalysis | null>(null);
  const [results, setResults] = useState<ExperimentResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const testRegions = useMemo(
    () => regions.filter((r) => r.isTest),
    [regions]
  );

  const controlRegions = useMemo(
    () => regions.filter((r) => r.isControl),
    [regions]
  );

  const unassignedRegions = useMemo(
    () => regions.filter((r) => !r.isTest && !r.isControl),
    [regions]
  );

  const toggleRegionAssignment = useCallback((regionId: string, type: "test" | "control") => {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== regionId) return r;
        if (type === "test") {
          return { ...r, isTest: !r.isTest, isControl: false };
        } else {
          return { ...r, isControl: !r.isControl, isTest: false };
        }
      })
    );
    setConfig((prev) => ({
      ...prev,
      testRegions: regions.filter((r) => r.isTest).map((r) => r.id),
      controlRegions: regions.filter((r) => r.isControl).map((r) => r.id),
    }));
  }, [regions]);

  const handleRunPowerAnalysis = async () => {
    setIsLoading(true);
    try {
      if (onRunPowerAnalysis) {
        const result = await onRunPowerAnalysis(config);
        setPowerAnalysis(result);
      } else {
        // Mock power analysis
        await new Promise((r) => setTimeout(r, 1500));
        setPowerAnalysis({
          sampleSize: testRegions.reduce((sum, r) => sum + r.population, 0),
          power: 0.82,
          mde: config.minimumDetectableEffect,
          duration: 28,
          expectedLift: 0.08,
        });
      }
      setStep("power");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveExperiment = async () => {
    setIsLoading(true);
    try {
      if (onSave) {
        await onSave(config);
      }
      setStep("monitor");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeResults = async () => {
    setIsLoading(true);
    try {
      if (onAnalyzeResults) {
        const result = await onAnalyzeResults("experiment-1");
        setResults(result);
      } else {
        // Mock results
        await new Promise((r) => setTimeout(r, 2000));
        setResults({
          lift: 0.072,
          liftCI: [0.032, 0.112],
          pValue: 0.0023,
          isSignificant: true,
          attPerRegion: Object.fromEntries(
            testRegions.map((r) => [r.id, Math.random() * 0.15])
          ),
        });
      }
      setStep("analyze");
    } finally {
      setIsLoading(false);
    }
  };

  const metrics = [
    { id: "conversions", label: "Conversions" },
    { id: "revenue", label: "Revenue" },
    { id: "signups", label: "Sign-ups" },
    { id: "engagement", label: "Engagement" },
  ];

  const steps = [
    { id: "design", label: "Design", number: 1 },
    { id: "power", label: "Power Analysis", number: 2 },
    { id: "monitor", label: "Monitor", number: 3 },
    { id: "analyze", label: "Analyze", number: 4 },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Geo-Lift Experiment
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Design and analyze geographic incrementality tests
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8 px-4">
        {steps.map((s, index) => (
          <div key={s.id} className="flex items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm ${
                step === s.id
                  ? "bg-primary text-white"
                  : steps.findIndex((st) => st.id === step) > index
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
              }`}
            >
              {s.number}
            </div>
            <span
              className={`ml-2 text-sm font-medium ${
                step === s.id
                  ? "text-primary"
                  : "text-gray-600 dark:text-gray-400"
              }`}
            >
              {s.label}
            </span>
            {index < steps.length - 1 && (
              <div className="w-24 h-0.5 mx-4 bg-gray-200 dark:bg-gray-700" />
            )}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Design Step */}
        {step === "design" && (
          <motion.div
            key="design"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            {/* Experiment Details */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Experiment Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Experiment Name</label>
                  <input
                    type="text"
                    value={config.name}
                    onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Q1 2024 Brand Campaign Test"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Primary Metric</label>
                  <select
                    value={config.primaryMetric}
                    onChange={(e) => setConfig((prev) => ({ ...prev, primaryMetric: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  >
                    {metrics.map((m) => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Start Date</label>
                  <input
                    type="date"
                    value={config.startDate}
                    onChange={(e) => setConfig((prev) => ({ ...prev, startDate: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={config.endDate}
                    onChange={(e) => setConfig((prev) => ({ ...prev, endDate: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={config.description}
                    onChange={(e) => setConfig((prev) => ({ ...prev, description: e.target.value }))}
                    placeholder="Describe the purpose of this experiment..."
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  />
                </div>
              </div>
            </div>

            {/* Region Selection */}
            <div className="grid grid-cols-3 gap-6">
              {/* Unassigned Regions */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
                <h4 className="font-semibold mb-3 text-gray-700 dark:text-gray-300">
                  Available Regions ({unassignedRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {unassignedRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => toggleRegionAssignment(region.id, "test")}
                            className="px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded"
                          >
                            + Test
                          </button>
                          <button
                            onClick={() => toggleRegionAssignment(region.id, "control")}
                            className="px-2 py-1 text-xs bg-gray-100 text-gray-700 dark:bg-gray-600 dark:text-gray-300 rounded"
                          >
                            + Control
                          </button>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Pop: {region.population.toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Test Regions */}
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 shadow-sm border border-blue-200 dark:border-blue-800">
                <h4 className="font-semibold mb-3 text-blue-700 dark:text-blue-300">
                  Test Regions ({testRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {testRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-white dark:bg-gray-800 rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <button
                          onClick={() => toggleRegionAssignment(region.id, "test")}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 rounded"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Pop: {region.population.toLocaleString()}
                      </div>
                    </div>
                  ))}
                  {testRegions.length === 0 && (
                    <p className="text-sm text-blue-600 dark:text-blue-400">
                      Add regions to test group
                    </p>
                  )}
                </div>
              </div>

              {/* Control Regions */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
                <h4 className="font-semibold mb-3 text-gray-700 dark:text-gray-300">
                  Control Regions ({controlRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {controlRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-white dark:bg-gray-700 rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <button
                          onClick={() => toggleRegionAssignment(region.id, "control")}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 rounded"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Pop: {region.population.toLocaleString()}
                      </div>
                    </div>
                  ))}
                  {controlRegions.length === 0 && (
                    <p className="text-sm text-gray-500">
                      Add regions to control group
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Parameters */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Statistical Parameters</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Confidence Level</label>
                  <select
                    value={config.confidenceLevel}
                    onChange={(e) => setConfig((prev) => ({ ...prev, confidenceLevel: parseFloat(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  >
                    <option value={0.9}>90%</option>
                    <option value={0.95}>95%</option>
                    <option value={0.99}>99%</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Minimum Detectable Effect</label>
                  <select
                    value={config.minimumDetectableEffect}
                    onChange={(e) => setConfig((prev) => ({ ...prev, minimumDetectableEffect: parseFloat(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                  >
                    <option value={0.03}>3%</option>
                    <option value={0.05}>5%</option>
                    <option value={0.1}>10%</option>
                    <option value={0.15}>15%</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleRunPowerAnalysis}
                disabled={testRegions.length === 0 || controlRegions.length === 0 || isLoading}
                className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? "Running Analysis..." : "Run Power Analysis"}
              </button>
            </div>
          </motion.div>
        )}

        {/* Power Analysis Step */}
        {step === "power" && powerAnalysis && (
          <motion.div
            key="power"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Power Analysis Results</h3>
              <div className="grid grid-cols-4 gap-6">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-primary">
                    {(powerAnalysis.power * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Statistical Power
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">
                    {(powerAnalysis.mde * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Minimum Detectable Effect
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">
                    {powerAnalysis.duration}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Recommended Days
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {powerAnalysis.sampleSize.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Test Population
                  </div>
                </div>
              </div>

              {powerAnalysis.power >= 0.8 ? (
                <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <p className="text-green-700 dark:text-green-300">
                    Your experiment design has sufficient power ({(powerAnalysis.power * 100).toFixed(0)}% &gt;= 80%) to detect a {(powerAnalysis.mde * 100).toFixed(1)}% lift.
                  </p>
                </div>
              ) : (
                <div className="mt-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-yellow-700 dark:text-yellow-300">
                    Your experiment may have insufficient power. Consider adding more regions or increasing the test duration.
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep("design")}
                className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Back to Design
              </button>
              <button
                onClick={handleSaveExperiment}
                disabled={isLoading}
                className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? "Saving..." : "Launch Experiment"}
              </button>
            </div>
          </motion.div>
        )}

        {/* Monitor Step */}
        {step === "monitor" && (
          <motion.div
            key="monitor"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Experiment Running</h3>
                <span className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded-full text-sm">
                  Active
                </span>
              </div>
              <p className="text-gray-600 dark:text-gray-400">
                Your experiment is now live. Data is being collected from {testRegions.length} test regions
                and {controlRegions.length} control regions.
              </p>

              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Estimated completion: {powerAnalysis?.duration || 28} days from start date
                </p>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleAnalyzeResults}
                disabled={isLoading}
                className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? "Analyzing..." : "Analyze Results"}
              </button>
            </div>
          </motion.div>
        )}

        {/* Analyze Step */}
        {step === "analyze" && results && (
          <motion.div
            key="analyze"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Experiment Results</h3>

              <div className="grid grid-cols-3 gap-6 mb-6">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className={`text-3xl font-bold ${results.lift >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {results.lift >= 0 ? "+" : ""}{(results.lift * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Measured Lift
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">
                    [{(results.liftCI[0] * 100).toFixed(1)}%, {(results.liftCI[1] * 100).toFixed(1)}%]
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    95% Confidence Interval
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {results.pValue.toFixed(4)}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    P-Value
                  </div>
                </div>
              </div>

              {results.isSignificant ? (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <p className="text-green-700 dark:text-green-300 font-medium">
                    Statistically Significant Result
                  </p>
                  <p className="text-green-600 dark:text-green-400 text-sm mt-1">
                    The campaign drove a {(results.lift * 100).toFixed(1)}% lift in {config.primaryMetric} (p = {results.pValue.toFixed(4)})
                  </p>
                </div>
              ) : (
                <div className="p-4 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg">
                  <p className="text-gray-700 dark:text-gray-300 font-medium">
                    No Significant Effect Detected
                  </p>
                  <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
                    The experiment did not detect a statistically significant lift at the {(config.confidenceLevel * 100)}% confidence level.
                  </p>
                </div>
              )}
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h4 className="font-semibold mb-4">Lift by Region</h4>
              <div className="space-y-3">
                {Object.entries(results.attPerRegion).map(([regionId, lift]) => {
                  const region = regions.find((r) => r.id === regionId);
                  return (
                    <div key={regionId} className="flex items-center gap-4">
                      <span className="w-32 text-sm font-medium">{region?.name || regionId}</span>
                      <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${lift >= 0 ? "bg-green-500" : "bg-red-500"}`}
                          style={{ width: `${Math.abs(lift) * 500}%` }}
                        />
                      </div>
                      <span className={`w-16 text-sm font-medium ${lift >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {lift >= 0 ? "+" : ""}{(lift * 100).toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep("design")}
                className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                New Experiment
              </button>
              <button className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary/90">
                Export Report
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default GeoLiftExperiment;
