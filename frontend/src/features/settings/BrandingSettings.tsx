/**
 * Branding Settings Component
 *
 * UI for managing white-label branding configuration.
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { BrandingConfig, BrandColors } from "../../config/branding";
import { defaultBranding, getBrandingManager } from "../../config/branding";

interface BrandingSettingsProps {
  initialConfig?: Partial<BrandingConfig>;
  onSave?: (config: BrandingConfig) => Promise<void>;
  canEdit?: boolean;
}

interface ColorInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

function ColorInput({ label, value, onChange, disabled }: ColorInputProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 w-32">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={hslToHex(value)}
          onChange={(e) => onChange(hexToHsl(e.target.value))}
          disabled={disabled}
          className="w-10 h-10 rounded border border-gray-300 dark:border-gray-600 cursor-pointer disabled:opacity-50"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-40 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
        />
      </div>
    </div>
  );
}

// Helper functions for color conversion
function hslToHex(hsl: string): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return "#000000";

  const h = parseInt(match[1]) / 360;
  const s = parseInt(match[2]) / 100;
  const l = parseInt(match[3]) / 100;

  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  const toHex = (x: number) => {
    const hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function hexToHsl(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return "hsl(0, 0%, 0%)";

  const r = parseInt(result[1], 16) / 255;
  const g = parseInt(result[2], 16) / 255;
  const b = parseInt(result[3], 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return `hsl(${Math.round(h * 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%)`;
}

export function BrandingSettings({
  initialConfig,
  onSave,
  canEdit = true,
}: BrandingSettingsProps) {
  const [config, setConfig] = useState<BrandingConfig>(() => {
    const manager = getBrandingManager(initialConfig);
    return manager.getConfig();
  });
  const [activeTab, setActiveTab] = useState<"general" | "colors" | "typography" | "features">("general");
  const [isSaving, setIsSaving] = useState(false);
  const [previewMode, setPreviewMode] = useState<"light" | "dark">("light");

  const updateConfig = useCallback((updates: Partial<BrandingConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  const updateColors = useCallback(
    (mode: "light" | "dark", colorKey: keyof BrandColors, value: string) => {
      setConfig((prev) => ({
        ...prev,
        colors: {
          ...prev.colors,
          [mode]: {
            ...prev.colors[mode],
            [colorKey]: value,
          },
        },
      }));
    },
    []
  );

  const handleSave = async () => {
    if (!onSave) return;

    setIsSaving(true);
    try {
      await onSave(config);
      // Apply branding after successful save
      getBrandingManager().updateConfig(config);
    } catch (error) {
      console.error("Failed to save branding:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setConfig(defaultBranding);
  };

  const tabs = [
    { id: "general" as const, label: "General" },
    { id: "colors" as const, label: "Colors" },
    { id: "typography" as const, label: "Typography" },
    { id: "features" as const, label: "Features" },
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Branding Settings
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Customize the appearance and branding of your analytics platform.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {/* General Tab */}
          {activeTab === "general" && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Basic Information</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Platform Name</label>
                    <input
                      type="text"
                      value={config.name}
                      onChange={(e) => updateConfig({ name: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Tagline</label>
                    <input
                      type="text"
                      value={config.tagline || ""}
                      onChange={(e) => updateConfig({ tagline: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Description</label>
                    <textarea
                      value={config.description || ""}
                      onChange={(e) => updateConfig({ description: e.target.value })}
                      disabled={!canEdit}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Logos</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Main Logo URL</label>
                    <input
                      type="text"
                      value={config.logo.src}
                      onChange={(e) =>
                        updateConfig({ logo: { ...config.logo, src: e.target.value } })
                      }
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Favicon URL</label>
                    <input
                      type="text"
                      value={config.favicon || ""}
                      onChange={(e) => updateConfig({ favicon: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">URLs</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Support URL</label>
                    <input
                      type="url"
                      value={config.supportUrl || ""}
                      onChange={(e) => updateConfig({ supportUrl: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Documentation URL</label>
                    <input
                      type="url"
                      value={config.documentationUrl || ""}
                      onChange={(e) => updateConfig({ documentationUrl: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Privacy Policy URL</label>
                    <input
                      type="url"
                      value={config.privacyPolicyUrl || ""}
                      onChange={(e) => updateConfig({ privacyPolicyUrl: e.target.value })}
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Colors Tab */}
          {activeTab === "colors" && (
            <div className="space-y-6">
              {/* Preview Mode Toggle */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setPreviewMode("light")}
                  className={`px-3 py-1 text-sm rounded-md ${
                    previewMode === "light"
                      ? "bg-primary text-white"
                      : "bg-gray-200 dark:bg-gray-700"
                  }`}
                >
                  Light Mode
                </button>
                <button
                  onClick={() => setPreviewMode("dark")}
                  className={`px-3 py-1 text-sm rounded-md ${
                    previewMode === "dark"
                      ? "bg-primary text-white"
                      : "bg-gray-200 dark:bg-gray-700"
                  }`}
                >
                  Dark Mode
                </button>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">
                  {previewMode === "light" ? "Light Mode" : "Dark Mode"} Colors
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <ColorInput
                    label="Primary"
                    value={config.colors[previewMode].primary}
                    onChange={(v) => updateColors(previewMode, "primary", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Secondary"
                    value={config.colors[previewMode].secondary}
                    onChange={(v) => updateColors(previewMode, "secondary", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Accent"
                    value={config.colors[previewMode].accent}
                    onChange={(v) => updateColors(previewMode, "accent", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Background"
                    value={config.colors[previewMode].background}
                    onChange={(v) => updateColors(previewMode, "background", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Foreground"
                    value={config.colors[previewMode].foreground}
                    onChange={(v) => updateColors(previewMode, "foreground", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Success"
                    value={config.colors[previewMode].success}
                    onChange={(v) => updateColors(previewMode, "success", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Warning"
                    value={config.colors[previewMode].warning}
                    onChange={(v) => updateColors(previewMode, "warning", v)}
                    disabled={!canEdit}
                  />
                  <ColorInput
                    label="Destructive"
                    value={config.colors[previewMode].destructive}
                    onChange={(v) => updateColors(previewMode, "destructive", v)}
                    disabled={!canEdit}
                  />
                </div>
              </div>

              {/* Color Preview */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Preview</h3>
                <div
                  className="p-4 rounded-lg"
                  style={{
                    backgroundColor: config.colors[previewMode].background,
                    color: config.colors[previewMode].foreground,
                  }}
                >
                  <div className="flex gap-2 mb-4">
                    <button
                      className="px-4 py-2 rounded-md text-sm font-medium"
                      style={{
                        backgroundColor: config.colors[previewMode].primary,
                        color: config.colors[previewMode].primaryForeground,
                      }}
                    >
                      Primary
                    </button>
                    <button
                      className="px-4 py-2 rounded-md text-sm font-medium"
                      style={{
                        backgroundColor: config.colors[previewMode].secondary,
                        color: config.colors[previewMode].secondaryForeground,
                      }}
                    >
                      Secondary
                    </button>
                    <button
                      className="px-4 py-2 rounded-md text-sm font-medium"
                      style={{
                        backgroundColor: config.colors[previewMode].accent,
                        color: config.colors[previewMode].accentForeground,
                      }}
                    >
                      Accent
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: config.colors[previewMode].success,
                        color: config.colors[previewMode].successForeground,
                      }}
                    >
                      Success
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: config.colors[previewMode].warning,
                        color: config.colors[previewMode].warningForeground,
                      }}
                    >
                      Warning
                    </span>
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: config.colors[previewMode].destructive,
                        color: config.colors[previewMode].destructiveForeground,
                      }}
                    >
                      Destructive
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Typography Tab */}
          {activeTab === "typography" && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Font Settings</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Body Font Family</label>
                    <select
                      value={config.typography.fontFamily}
                      onChange={(e) =>
                        updateConfig({
                          typography: { ...config.typography, fontFamily: e.target.value },
                        })
                      }
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    >
                      <option value="Inter, system-ui, sans-serif">Inter</option>
                      <option value="Roboto, system-ui, sans-serif">Roboto</option>
                      <option value="Open Sans, system-ui, sans-serif">Open Sans</option>
                      <option value="Lato, system-ui, sans-serif">Lato</option>
                      <option value="system-ui, sans-serif">System UI</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Heading Font Family</label>
                    <select
                      value={config.typography.headingFontFamily || config.typography.fontFamily}
                      onChange={(e) =>
                        updateConfig({
                          typography: { ...config.typography, headingFontFamily: e.target.value },
                        })
                      }
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    >
                      <option value="Inter, system-ui, sans-serif">Inter</option>
                      <option value="Roboto, system-ui, sans-serif">Roboto</option>
                      <option value="Poppins, system-ui, sans-serif">Poppins</option>
                      <option value="Montserrat, system-ui, sans-serif">Montserrat</option>
                      <option value="system-ui, sans-serif">System UI</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Base Font Size</label>
                    <select
                      value={config.typography.baseFontSize}
                      onChange={(e) =>
                        updateConfig({
                          typography: { ...config.typography, baseFontSize: e.target.value },
                        })
                      }
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    >
                      <option value="14px">Small (14px)</option>
                      <option value="16px">Medium (16px)</option>
                      <option value="18px">Large (18px)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Typography Preview */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Preview</h3>
                <div style={{ fontFamily: config.typography.fontFamily }}>
                  <h1
                    className="text-3xl font-bold mb-2"
                    style={{ fontFamily: config.typography.headingFontFamily }}
                  >
                    Heading 1
                  </h1>
                  <h2
                    className="text-2xl font-semibold mb-2"
                    style={{ fontFamily: config.typography.headingFontFamily }}
                  >
                    Heading 2
                  </h2>
                  <h3
                    className="text-xl font-medium mb-4"
                    style={{ fontFamily: config.typography.headingFontFamily }}
                  >
                    Heading 3
                  </h3>
                  <p className="text-base mb-2" style={{ fontSize: config.typography.baseFontSize }}>
                    This is body text using your selected font settings. The quick brown fox jumps
                    over the lazy dog.
                  </p>
                  <p className="text-sm text-gray-500">
                    Smaller text for labels and secondary content.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Features Tab */}
          {activeTab === "features" && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">UI Features</h3>
                <div className="space-y-4">
                  {Object.entries(config.features).map(([key, value]) => (
                    <label key={key} className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={value}
                        onChange={(e) =>
                          updateConfig({
                            features: { ...config.features, [key]: e.target.checked },
                          })
                        }
                        disabled={!canEdit}
                        className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary disabled:opacity-50"
                      />
                      <span className="text-sm">
                        {key
                          .replace(/([A-Z])/g, " $1")
                          .replace(/^./, (str) => str.toUpperCase())}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Footer Settings</h3>
                <div className="space-y-4">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={config.footer.show}
                      onChange={(e) =>
                        updateConfig({
                          footer: { ...config.footer, show: e.target.checked },
                        })
                      }
                      disabled={!canEdit}
                      className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary disabled:opacity-50"
                    />
                    <span className="text-sm">Show Footer</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={config.footer.showPoweredBy}
                      onChange={(e) =>
                        updateConfig({
                          footer: { ...config.footer, showPoweredBy: e.target.checked },
                        })
                      }
                      disabled={!canEdit}
                      className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary disabled:opacity-50"
                    />
                    <span className="text-sm">Show "Powered By" Attribution</span>
                  </label>
                  <div>
                    <label className="block text-sm font-medium mb-1">Footer Text</label>
                    <input
                      type="text"
                      value={config.footer.text || ""}
                      onChange={(e) =>
                        updateConfig({
                          footer: { ...config.footer, text: e.target.value },
                        })
                      }
                      disabled={!canEdit}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Action Buttons */}
      {canEdit && (
        <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleReset}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      )}
    </div>
  );
}

export default BrandingSettings;
