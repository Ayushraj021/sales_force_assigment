/**
 * Response Curve Editor
 *
 * Interactive editor for marketing response curves (saturation and adstock).
 * Allows real-time parameter adjustment with visual feedback.
 */

import { useState, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

// Types
type CurveType = 'hill' | 'logistic' | 'tanh' | 'power';
type AdstockType = 'geometric' | 'weibull';

interface SaturationParams {
  type: CurveType;
  L: number; // Maximum effect
  k: number; // Steepness/growth rate
  x0: number; // Midpoint
  alpha?: number; // Power parameter (for power curve)
}

interface AdstockParams {
  type: AdstockType;
  theta: number; // Decay rate (geometric)
  shape?: number; // Shape parameter (weibull)
  scale?: number; // Scale parameter (weibull)
  maxLag: number;
}

interface ResponseCurveEditorProps {
  className?: string;
  initialSaturation?: Partial<SaturationParams>;
  initialAdstock?: Partial<AdstockParams>;
  onSaturationChange?: (params: SaturationParams) => void;
  onAdstockChange?: (params: AdstockParams) => void;
  showExamples?: boolean;
  width?: number;
  height?: number;
}

// Default parameters
const DEFAULT_SATURATION: SaturationParams = {
  type: 'hill',
  L: 1,
  k: 2,
  x0: 0.5,
  alpha: 0.5,
};

const DEFAULT_ADSTOCK: AdstockParams = {
  type: 'geometric',
  theta: 0.7,
  shape: 2,
  scale: 1,
  maxLag: 8,
};

// Saturation curve functions
const saturationFunctions: Record<CurveType, (x: number, params: SaturationParams) => number> = {
  hill: (x, { L, k, x0 }) => {
    if (x <= 0) return 0;
    const xk = Math.pow(x, k);
    const x0k = Math.pow(x0, k);
    return L * (xk / (xk + x0k));
  },
  logistic: (x, { L, k, x0 }) => {
    return L / (1 + Math.exp(-k * (x - x0)));
  },
  tanh: (x, { L, k, x0 }) => {
    return L * (Math.tanh(k * (x - x0)) + 1) / 2;
  },
  power: (x, { L, alpha = 0.5 }) => {
    return L * Math.pow(x, alpha);
  },
};

// Adstock functions
const adstockFunctions: Record<AdstockType, (lag: number, params: AdstockParams) => number> = {
  geometric: (lag, { theta }) => {
    return Math.pow(theta, lag);
  },
  weibull: (lag, { shape = 2, scale = 1 }) => {
    if (lag === 0) return 1;
    const x = lag / scale;
    return Math.exp(-Math.pow(x, shape));
  },
};

export function ResponseCurveEditor({
  className,
  initialSaturation,
  initialAdstock,
  onSaturationChange,
  onAdstockChange,
  showExamples = true,
  width = 400,
  height = 300,
}: ResponseCurveEditorProps) {
  // State for saturation parameters
  const [saturation, setSaturation] = useState<SaturationParams>({
    ...DEFAULT_SATURATION,
    ...initialSaturation,
  });

  // State for adstock parameters
  const [adstock, setAdstock] = useState<AdstockParams>({
    ...DEFAULT_ADSTOCK,
    ...initialAdstock,
  });

  // Update saturation
  const updateSaturation = useCallback(
    (updates: Partial<SaturationParams>) => {
      const newParams = { ...saturation, ...updates };
      setSaturation(newParams);
      onSaturationChange?.(newParams);
    },
    [saturation, onSaturationChange]
  );

  // Update adstock
  const updateAdstock = useCallback(
    (updates: Partial<AdstockParams>) => {
      const newParams = { ...adstock, ...updates };
      setAdstock(newParams);
      onAdstockChange?.(newParams);
    },
    [adstock, onAdstockChange]
  );

  // Generate saturation curve data
  const saturationData = useMemo(() => {
    const points: Array<{ x: number; y: number }> = [];
    const fn = saturationFunctions[saturation.type];

    for (let i = 0; i <= 100; i++) {
      const x = i / 100;
      const y = fn(x, saturation);
      points.push({ x, y });
    }

    return points;
  }, [saturation]);

  // Generate adstock decay data
  const adstockData = useMemo(() => {
    const points: Array<{ lag: number; weight: number }> = [];
    const fn = adstockFunctions[adstock.type];

    for (let lag = 0; lag <= adstock.maxLag; lag++) {
      const weight = fn(lag, adstock);
      points.push({ lag, weight });
    }

    return points;
  }, [adstock]);

  // Chart margins
  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Scales for saturation chart
  const xScaleSat = useMemo(
    () => d3.scaleLinear().domain([0, 1]).range([0, innerWidth]),
    [innerWidth]
  );
  const yScaleSat = useMemo(
    () => d3.scaleLinear().domain([0, saturation.L * 1.1]).range([innerHeight, 0]),
    [innerHeight, saturation.L]
  );

  // Scales for adstock chart
  const xScaleAds = useMemo(
    () => d3.scaleLinear().domain([0, adstock.maxLag]).range([0, innerWidth]),
    [innerWidth, adstock.maxLag]
  );
  const yScaleAds = useMemo(
    () => d3.scaleLinear().domain([0, 1.1]).range([innerHeight, 0]),
    [innerHeight]
  );

  // Line generators
  const lineSat = useMemo(
    () =>
      d3.line<{ x: number; y: number }>()
        .x((d) => xScaleSat(d.x))
        .y((d) => yScaleSat(d.y))
        .curve(d3.curveMonotoneX),
    [xScaleSat, yScaleSat]
  );

  const lineAds = useMemo(
    () =>
      d3.line<{ lag: number; weight: number }>()
        .x((d) => xScaleAds(d.lag))
        .y((d) => yScaleAds(d.weight))
        .curve(d3.curveMonotoneX),
    [xScaleAds, yScaleAds]
  );

  // Area under adstock curve
  const areaAds = useMemo(
    () =>
      d3.area<{ lag: number; weight: number }>()
        .x((d) => xScaleAds(d.lag))
        .y0(innerHeight)
        .y1((d) => yScaleAds(d.weight))
        .curve(d3.curveMonotoneX),
    [xScaleAds, yScaleAds, innerHeight]
  );

  // Calculate total adstock weight
  const totalAdstockWeight = useMemo(
    () => adstockData.reduce((sum, d) => sum + d.weight, 0),
    [adstockData]
  );

  return (
    <div className={cn('space-y-6', className)}>
      <Tabs defaultValue="saturation">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="saturation">Saturation Curve</TabsTrigger>
          <TabsTrigger value="adstock">Adstock Decay</TabsTrigger>
        </TabsList>

        {/* Saturation Curve Tab */}
        <TabsContent value="saturation" className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Saturation Function</CardTitle>
              <CardDescription>
                Models diminishing returns as spend increases
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Curve Type Selection */}
              <div className="flex gap-2">
                {(['hill', 'logistic', 'tanh', 'power'] as CurveType[]).map((type) => (
                  <Button
                    key={type}
                    variant={saturation.type === type ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => updateSaturation({ type })}
                    className="capitalize"
                  >
                    {type}
                  </Button>
                ))}
              </div>

              {/* Chart */}
              <svg width={width} height={height}>
                <g transform={`translate(${margin.left}, ${margin.top})`}>
                  {/* Grid lines */}
                  {yScaleSat.ticks(5).map((tick) => (
                    <g key={tick}>
                      <line
                        x1={0}
                        x2={innerWidth}
                        y1={yScaleSat(tick)}
                        y2={yScaleSat(tick)}
                        stroke="hsl(var(--muted))"
                        strokeDasharray="3,3"
                      />
                      <text
                        x={-8}
                        y={yScaleSat(tick)}
                        textAnchor="end"
                        dominantBaseline="middle"
                        className="text-xs fill-muted-foreground"
                      >
                        {tick.toFixed(1)}
                      </text>
                    </g>
                  ))}

                  {/* X-axis */}
                  <line
                    x1={0}
                    x2={innerWidth}
                    y1={innerHeight}
                    y2={innerHeight}
                    stroke="hsl(var(--border))"
                  />
                  {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
                    <text
                      key={tick}
                      x={xScaleSat(tick)}
                      y={innerHeight + 16}
                      textAnchor="middle"
                      className="text-xs fill-muted-foreground"
                    >
                      {tick}
                    </text>
                  ))}

                  {/* Axis labels */}
                  <text
                    x={innerWidth / 2}
                    y={innerHeight + 32}
                    textAnchor="middle"
                    className="text-xs fill-muted-foreground"
                  >
                    Spend (normalized)
                  </text>
                  <text
                    x={-innerHeight / 2}
                    y={-35}
                    textAnchor="middle"
                    transform="rotate(-90)"
                    className="text-xs fill-muted-foreground"
                  >
                    Response
                  </text>

                  {/* Curve */}
                  <motion.path
                    d={lineSat(saturationData) || ''}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2.5}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.5 }}
                  />

                  {/* Half-saturation point marker */}
                  {saturation.type !== 'power' && (
                    <g>
                      <circle
                        cx={xScaleSat(saturation.x0)}
                        cy={yScaleSat(saturation.L / 2)}
                        r={5}
                        fill="hsl(var(--primary))"
                        stroke="hsl(var(--background))"
                        strokeWidth={2}
                      />
                      <text
                        x={xScaleSat(saturation.x0) + 10}
                        y={yScaleSat(saturation.L / 2)}
                        className="text-xs fill-muted-foreground"
                        dominantBaseline="middle"
                      >
                        x₀ = {saturation.x0.toFixed(2)}
                      </text>
                    </g>
                  )}
                </g>
              </svg>

              {/* Parameter Controls */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="flex justify-between">
                    <span>Maximum Effect (L)</span>
                    <span className="text-muted-foreground">{saturation.L.toFixed(2)}</span>
                  </Label>
                  <Slider
                    value={[saturation.L]}
                    onValueChange={([v]) => updateSaturation({ L: v })}
                    min={0.1}
                    max={2}
                    step={0.05}
                  />
                </div>

                {saturation.type !== 'power' && (
                  <>
                    <div className="space-y-2">
                      <Label className="flex justify-between">
                        <span>Steepness (k)</span>
                        <span className="text-muted-foreground">{saturation.k.toFixed(2)}</span>
                      </Label>
                      <Slider
                        value={[saturation.k]}
                        onValueChange={([v]) => updateSaturation({ k: v })}
                        min={0.5}
                        max={10}
                        step={0.1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="flex justify-between">
                        <span>Half-saturation (x₀)</span>
                        <span className="text-muted-foreground">{saturation.x0.toFixed(2)}</span>
                      </Label>
                      <Slider
                        value={[saturation.x0]}
                        onValueChange={([v]) => updateSaturation({ x0: v })}
                        min={0.1}
                        max={0.9}
                        step={0.05}
                      />
                    </div>
                  </>
                )}

                {saturation.type === 'power' && (
                  <div className="space-y-2">
                    <Label className="flex justify-between">
                      <span>Power (α)</span>
                      <span className="text-muted-foreground">{(saturation.alpha || 0.5).toFixed(2)}</span>
                    </Label>
                    <Slider
                      value={[saturation.alpha || 0.5]}
                      onValueChange={([v]) => updateSaturation({ alpha: v })}
                      min={0.1}
                      max={1}
                      step={0.05}
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Adstock Tab */}
        <TabsContent value="adstock" className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Adstock Decay</CardTitle>
              <CardDescription>
                Models how advertising effect decays over time
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Decay Type Selection */}
              <div className="flex gap-2">
                {(['geometric', 'weibull'] as AdstockType[]).map((type) => (
                  <Button
                    key={type}
                    variant={adstock.type === type ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => updateAdstock({ type })}
                    className="capitalize"
                  >
                    {type}
                  </Button>
                ))}
              </div>

              {/* Chart */}
              <svg width={width} height={height}>
                <g transform={`translate(${margin.left}, ${margin.top})`}>
                  {/* Grid lines */}
                  {yScaleAds.ticks(5).map((tick) => (
                    <g key={tick}>
                      <line
                        x1={0}
                        x2={innerWidth}
                        y1={yScaleAds(tick)}
                        y2={yScaleAds(tick)}
                        stroke="hsl(var(--muted))"
                        strokeDasharray="3,3"
                      />
                      <text
                        x={-8}
                        y={yScaleAds(tick)}
                        textAnchor="end"
                        dominantBaseline="middle"
                        className="text-xs fill-muted-foreground"
                      >
                        {tick.toFixed(1)}
                      </text>
                    </g>
                  ))}

                  {/* X-axis */}
                  <line
                    x1={0}
                    x2={innerWidth}
                    y1={innerHeight}
                    y2={innerHeight}
                    stroke="hsl(var(--border))"
                  />
                  {d3.range(0, adstock.maxLag + 1).map((tick) => (
                    <text
                      key={tick}
                      x={xScaleAds(tick)}
                      y={innerHeight + 16}
                      textAnchor="middle"
                      className="text-xs fill-muted-foreground"
                    >
                      {tick}
                    </text>
                  ))}

                  {/* Axis labels */}
                  <text
                    x={innerWidth / 2}
                    y={innerHeight + 32}
                    textAnchor="middle"
                    className="text-xs fill-muted-foreground"
                  >
                    Lag (periods)
                  </text>
                  <text
                    x={-innerHeight / 2}
                    y={-35}
                    textAnchor="middle"
                    transform="rotate(-90)"
                    className="text-xs fill-muted-foreground"
                  >
                    Weight
                  </text>

                  {/* Area fill */}
                  <motion.path
                    d={areaAds(adstockData) || ''}
                    fill="hsl(var(--primary) / 0.2)"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  />

                  {/* Curve */}
                  <motion.path
                    d={lineAds(adstockData) || ''}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2.5}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.5 }}
                  />

                  {/* Data points */}
                  {adstockData.map((d) => (
                    <circle
                      key={d.lag}
                      cx={xScaleAds(d.lag)}
                      cy={yScaleAds(d.weight)}
                      r={4}
                      fill="hsl(var(--primary))"
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  ))}
                </g>
              </svg>

              {/* Stats */}
              <div className="flex gap-4 text-sm">
                <div className="bg-muted/50 rounded-md px-3 py-2">
                  <div className="text-muted-foreground text-xs">Total Weight</div>
                  <div className="font-medium">{totalAdstockWeight.toFixed(2)}</div>
                </div>
                <div className="bg-muted/50 rounded-md px-3 py-2">
                  <div className="text-muted-foreground text-xs">Half-life</div>
                  <div className="font-medium">
                    {adstock.type === 'geometric'
                      ? (Math.log(0.5) / Math.log(adstock.theta)).toFixed(1)
                      : (adstock.scale! * Math.pow(Math.log(2), 1 / adstock.shape!)).toFixed(1)
                    } periods
                  </div>
                </div>
              </div>

              {/* Parameter Controls */}
              <div className="space-y-4">
                {adstock.type === 'geometric' && (
                  <div className="space-y-2">
                    <Label className="flex justify-between">
                      <span>Decay Rate (θ)</span>
                      <span className="text-muted-foreground">{adstock.theta.toFixed(2)}</span>
                    </Label>
                    <Slider
                      value={[adstock.theta]}
                      onValueChange={([v]) => updateAdstock({ theta: v })}
                      min={0.1}
                      max={0.95}
                      step={0.05}
                    />
                  </div>
                )}

                {adstock.type === 'weibull' && (
                  <>
                    <div className="space-y-2">
                      <Label className="flex justify-between">
                        <span>Shape (k)</span>
                        <span className="text-muted-foreground">{(adstock.shape || 2).toFixed(2)}</span>
                      </Label>
                      <Slider
                        value={[adstock.shape || 2]}
                        onValueChange={([v]) => updateAdstock({ shape: v })}
                        min={0.5}
                        max={5}
                        step={0.1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="flex justify-between">
                        <span>Scale (λ)</span>
                        <span className="text-muted-foreground">{(adstock.scale || 1).toFixed(2)}</span>
                      </Label>
                      <Slider
                        value={[adstock.scale || 1]}
                        onValueChange={([v]) => updateAdstock({ scale: v })}
                        min={0.5}
                        max={4}
                        step={0.1}
                      />
                    </div>
                  </>
                )}

                <div className="space-y-2">
                  <Label className="flex justify-between">
                    <span>Max Lag</span>
                    <span className="text-muted-foreground">{adstock.maxLag} periods</span>
                  </Label>
                  <Slider
                    value={[adstock.maxLag]}
                    onValueChange={([v]) => updateAdstock({ maxLag: Math.round(v) })}
                    min={4}
                    max={16}
                    step={1}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Example presets */}
      {showExamples && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Presets</CardTitle>
            <CardDescription>Common configurations for different media types</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateSaturation({ type: 'hill', L: 1, k: 2, x0: 0.5 });
                  updateAdstock({ type: 'geometric', theta: 0.7, maxLag: 8 });
                }}
              >
                TV / Video
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateSaturation({ type: 'hill', L: 1, k: 3, x0: 0.3 });
                  updateAdstock({ type: 'geometric', theta: 0.4, maxLag: 4 });
                }}
              >
                Digital / Search
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateSaturation({ type: 'logistic', L: 1, k: 5, x0: 0.4 });
                  updateAdstock({ type: 'geometric', theta: 0.85, maxLag: 12 });
                }}
              >
                Print / OOH
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateSaturation({ type: 'hill', L: 1, k: 2.5, x0: 0.4 });
                  updateAdstock({ type: 'weibull', shape: 2, scale: 2, maxLag: 8 });
                }}
              >
                Social Media
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default ResponseCurveEditor;
