/**
 * GeoLift Experiment Component
 *
 * UI for designing and analyzing geographic lift tests.
 */

import { useState, useCallback, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  useCreateGeoExperiment,
  useRunPowerAnalysis,
  useAnalyzeGeoExperiment,
  useGeoExperimentActions,
  useGeoExperiment,
} from "@/hooks/useGeoExperiments";

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
  experimentId?: string;
  regions?: Region[];
  onSave?: (config: ExperimentConfig) => Promise<void>;
  onRunPowerAnalysis?: (config: ExperimentConfig) => Promise<PowerAnalysis>;
  onAnalyzeResults?: (experimentId: string) => Promise<ExperimentResult>;
  onExperimentCreated?: (experimentId: string) => void;
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
  experimentId: initialExperimentId,
  regions: initialRegions = defaultRegions,
  onSave,
  onRunPowerAnalysis,
  onAnalyzeResults,
  onExperimentCreated,
}: GeoLiftExperimentProps) {
  const [step, setStep] = useState<"design" | "power" | "monitor" | "analyze">("design");
  const [regions, setRegions] = useState<Region[]>(initialRegions);
  const [experimentId, setExperimentId] = useState<string | undefined>(initialExperimentId);
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

  // API Hooks
  const { createExperiment, loading: createLoading, error: createError } = useCreateGeoExperiment();
  const { runPowerAnalysis: runPowerAnalysisAPI, loading: powerLoading, error: powerError } = useRunPowerAnalysis();
  const { analyzeExperiment, loading: analyzeLoading, error: analyzeError } = useAnalyzeGeoExperiment();
  const { markReady, startExperiment, loading: actionLoading, error: actionError } = useGeoExperimentActions();
  const { experiment: existingExperiment } = useGeoExperiment(initialExperimentId);

  const isLoading = createLoading || powerLoading || analyzeLoading || actionLoading;
  const apiError = createError || powerError || analyzeError || actionError;

  // Load existing experiment data if editing
  useEffect(() => {
    if (existingExperiment) {
      setConfig({
        name: existingExperiment.name,
        description: existingExperiment.description || "",
        startDate: existingExperiment.startDate || "",
        endDate: existingExperiment.endDate || "",
        testRegions: existingExperiment.testRegions || [],
        controlRegions: existingExperiment.controlRegions || [],
        primaryMetric: existingExperiment.primaryMetric || "conversions",
        secondaryMetrics: existingExperiment.secondaryMetrics || [],
        confidenceLevel: 0.95,
        minimumDetectableEffect: existingExperiment.minimumDetectableEffect || 0.05,
      });

      // Update regions based on experiment data
      setRegions((prev) =>
        prev.map((r) => ({
          ...r,
          isTest: existingExperiment.testRegions?.includes(r.id) || false,
          isControl: existingExperiment.controlRegions?.includes(r.id) || false,
        }))
      );

      // Set step based on status
      if (existingExperiment.status === "analyzed") {
        setStep("analyze");
      } else if (existingExperiment.status === "running" || existingExperiment.status === "completed") {
        setStep("monitor");
      } else if (existingExperiment.powerAnalysis) {
        setStep("power");
        const pa = existingExperiment.powerAnalysis as Record<string, number>;
        setPowerAnalysis({
          sampleSize: pa.required_sample_size || 0,
          power: pa.estimated_power || 0,
          mde: existingExperiment.minimumDetectableEffect || 0.05,
          duration: 28,
          expectedLift: 0.08,
        });
      }
    }
  }, [existingExperiment]);

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
    try {
      // If using custom callback
      if (onRunPowerAnalysis) {
        const result = await onRunPowerAnalysis(config);
        setPowerAnalysis(result);
        setStep("power");
        return;
      }

      // Create experiment first if not exists
      let currentExperimentId = experimentId;
      if (!currentExperimentId) {
        const created = await createExperiment({
          name: config.name || "New Geo Experiment",
          description: config.description,
          testRegions: testRegions.map((r) => r.id),
          controlRegions: controlRegions.map((r) => r.id),
          startDate: config.startDate || undefined,
          endDate: config.endDate || undefined,
          minimumDetectableEffect: config.minimumDetectableEffect,
          targetPower: 0.8,
          primaryMetric: config.primaryMetric,
          secondaryMetrics: config.secondaryMetrics.length > 0 ? config.secondaryMetrics : undefined,
        });

        if (created) {
          currentExperimentId = created.id;
          setExperimentId(created.id);
          onExperimentCreated?.(created.id);
        } else {
          console.error("Failed to create experiment");
          return;
        }
      }

      // Run power analysis via API
      const result = await runPowerAnalysisAPI({
        experimentId: currentExperimentId,
        expectedEffectSize: config.minimumDetectableEffect,
        significanceLevel: 1 - config.confidenceLevel,
      });

      if (result) {
        setPowerAnalysis({
          sampleSize: result.requiredSampleSize,
          power: result.estimatedPower,
          mde: result.minimumDetectableEffect,
          duration: 28,
          expectedLift: result.minimumDetectableEffect,
        });
        setStep("power");
      }
    } catch (err) {
      console.error("Power analysis failed:", err);
    }
  };

  const handleSaveExperiment = async () => {
    try {
      // If using custom callback
      if (onSave) {
        await onSave(config);
        setStep("monitor");
        return;
      }

      // Mark experiment as ready and start it
      if (experimentId) {
        const readySuccess = await markReady(experimentId);
        if (readySuccess) {
          const startSuccess = await startExperiment(experimentId);
          if (startSuccess) {
            setStep("monitor");
          }
        }
      }
    } catch (err) {
      console.error("Failed to save experiment:", err);
    }
  };

  const handleAnalyzeResults = async () => {
    try {
      // If using custom callback
      if (onAnalyzeResults && experimentId) {
        const result = await onAnalyzeResults(experimentId);
        setResults(result);
        setStep("analyze");
        return;
      }

      // Analyze via API
      if (experimentId) {
        const result = await analyzeExperiment(experimentId);
        if (result) {
          setResults({
            lift: result.relativeLift / 100,
            liftCI: [result.confidenceIntervalLower / result.controlMetricValue, result.confidenceIntervalUpper / result.controlMetricValue],
            pValue: result.pValue,
            isSignificant: result.isSignificant,
            attPerRegion: (result.regionLevelResults as Record<string, number>) || Object.fromEntries(
              testRegions.map((r) => [r.id, result.relativeLift / 100])
            ),
          });
          setStep("analyze");
        }
      }
    } catch (err) {
      console.error("Analysis failed:", err);
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
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Geo-Lift Experiment
        </h1>
        <p className="mt-2 text-gray-600">
          Design and analyze geographic incrementality tests
        </p>
      </div>

      {/* Error Display */}
      {apiError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{apiError}</p>
        </div>
      )}

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8 px-4">
        {steps.map((s, index) => (
          <div key={s.id} className="flex items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm ${
                step === s.id
                  ? "bg-primary-600 text-white"
                  : steps.findIndex((st) => st.id === step) > index
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-600"
              }`}
            >
              {s.number}
            </div>
            <span
              className={`ml-2 text-sm font-medium ${
                step === s.id
                  ? "text-primary-600"
                  : "text-gray-600"
              }`}
            >
              {s.label}
            </span>
            {index < steps.length - 1 && (
              <div className="w-24 h-0.5 mx-4 bg-gray-200" />
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
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Experiment Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Experiment Name</label>
                  <input
                    type="text"
                    value={config.name}
                    onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Q1 2024 Brand Campaign Test"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Primary Metric</label>
                  <select
                    value={config.primaryMetric}
                    onChange={(e) => setConfig((prev) => ({ ...prev, primaryMetric: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={config.endDate}
                    onChange={(e) => setConfig((prev) => ({ ...prev, endDate: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={config.description}
                    onChange={(e) => setConfig((prev) => ({ ...prev, description: e.target.value }))}
                    placeholder="Describe the purpose of this experiment..."
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  />
                </div>
              </div>
            </div>

            {/* Region Selection */}
            <div className="grid grid-cols-3 gap-6">
              {/* Unassigned Regions */}
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                <h4 className="font-semibold mb-3 text-gray-700">
                  Available Regions ({unassignedRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {unassignedRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => toggleRegionAssignment(region.id, "test")}
                            className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                          >
                            + Test
                          </button>
                          <button
                            onClick={() => toggleRegionAssignment(region.id, "control")}
                            className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
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
              <div className="bg-blue-50 rounded-lg p-4 shadow-sm border border-blue-200">
                <h4 className="font-semibold mb-3 text-blue-700">
                  Test Regions ({testRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {testRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-white rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <button
                          onClick={() => toggleRegionAssignment(region.id, "test")}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded"
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
                    <p className="text-sm text-blue-600">
                      Add regions to test group
                    </p>
                  )}
                </div>
              </div>

              {/* Control Regions */}
              <div className="bg-gray-50 rounded-lg p-4 shadow-sm border border-gray-200">
                <h4 className="font-semibold mb-3 text-gray-700">
                  Control Regions ({controlRegions.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {controlRegions.map((region) => (
                    <div
                      key={region.id}
                      className="p-3 bg-white rounded-lg"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{region.name}</span>
                        <button
                          onClick={() => toggleRegionAssignment(region.id, "control")}
                          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded"
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
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Statistical Parameters</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Confidence Level</label>
                  <select
                    value={config.confidenceLevel}
                    onChange={(e) => setConfig((prev) => ({ ...prev, confidenceLevel: parseFloat(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  >
                    <option value={0.03}>3%</option>
                    <option value={0.05}>5%</option>
                    <option value={0.1}>10%</option>
                    <option value={0.15}>15%</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={handleRunPowerAnalysis}
                disabled={testRegions.length === 0 || controlRegions.length === 0 || isLoading}
                className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Running Analysis..." : "Next: Run Power Analysis →"}
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
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Power Analysis Results</h3>
              <div className="grid grid-cols-4 gap-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-primary-600">
                    {(powerAnalysis.power * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Statistical Power
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">
                    {(powerAnalysis.mde * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Minimum Detectable Effect
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">
                    {powerAnalysis.duration}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Recommended Days
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {powerAnalysis.sampleSize.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Test Population
                  </div>
                </div>
              </div>

              {powerAnalysis.power >= 0.8 ? (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-700">
                    Your experiment design has sufficient power ({(powerAnalysis.power * 100).toFixed(0)}% &gt;= 80%) to detect a {(powerAnalysis.mde * 100).toFixed(1)}% lift.
                  </p>
                </div>
              ) : (
                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-700">
                    Your experiment may have insufficient power. Consider adding more regions or increasing the test duration.
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep("design")}
                className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Back to Design
              </button>
              <button
                onClick={handleSaveExperiment}
                disabled={isLoading}
                className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Saving..." : "Next: Launch Experiment →"}
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
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Experiment Running</h3>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                  Active
                </span>
              </div>
              <p className="text-gray-600">
                Your experiment is now live. Data is being collected from {testRegions.length} test regions
                and {controlRegions.length} control regions.
              </p>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-700">
                  Estimated completion: {powerAnalysis?.duration || 28} days from start date
                </p>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleAnalyzeResults}
                disabled={isLoading}
                className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Analyzing..." : "Next: Analyze Results →"}
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
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Experiment Results</h3>

              <div className="grid grid-cols-3 gap-6 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className={`text-3xl font-bold ${results.lift >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {results.lift >= 0 ? "+" : ""}{(results.lift * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Measured Lift
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">
                    [{(results.liftCI[0] * 100).toFixed(1)}%, {(results.liftCI[1] * 100).toFixed(1)}%]
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    95% Confidence Interval
                  </div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {results.pValue.toFixed(4)}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    P-Value
                  </div>
                </div>
              </div>

              {results.isSignificant ? (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-700 font-medium">
                    Statistically Significant Result
                  </p>
                  <p className="text-green-600 text-sm mt-1">
                    The campaign drove a {(results.lift * 100).toFixed(1)}% lift in {config.primaryMetric} (p = {results.pValue.toFixed(4)})
                  </p>
                </div>
              ) : (
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                  <p className="text-gray-700 font-medium">
                    No Significant Effect Detected
                  </p>
                  <p className="text-gray-600 text-sm mt-1">
                    The experiment did not detect a statistically significant lift at the {(config.confidenceLevel * 100)}% confidence level.
                  </p>
                </div>
              )}
            </div>

            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <h4 className="font-semibold mb-4">Lift by Region</h4>
              <div className="space-y-3">
                {Object.entries(results.attPerRegion).map(([regionId, lift]) => {
                  const region = regions.find((r) => r.id === regionId);
                  return (
                    <div key={regionId} className="flex items-center gap-4">
                      <span className="w-32 text-sm font-medium">{region?.name || regionId}</span>
                      <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
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
                onClick={() => {
                  setStep("design");
                  setExperimentId(undefined);
                  setResults(null);
                  setPowerAnalysis(null);
                  setConfig({
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
                  setRegions(defaultRegions);
                }}
                className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                New Experiment
              </button>
              <button
                onClick={() => {
                  // Export results as JSON for now
                  if (results && experimentId) {
                    const exportData = {
                      experimentId,
                      experimentName: config.name,
                      results: {
                        lift: results.lift,
                        liftCI: results.liftCI,
                        pValue: results.pValue,
                        isSignificant: results.isSignificant,
                      },
                      testRegions: testRegions.map(r => r.name),
                      controlRegions: controlRegions.map(r => r.name),
                      exportedAt: new Date().toISOString(),
                    };
                    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `geo-experiment-${experimentId}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }
                }}
                className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
              >
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
